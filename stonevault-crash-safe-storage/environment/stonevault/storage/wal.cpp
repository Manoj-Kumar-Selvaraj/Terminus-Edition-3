#include "wal.hpp"
#include "codec.hpp"

#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <stdexcept>
#include <sys/types.h>
#include <unistd.h>
#include <utility>

namespace stonevault {

namespace {

std::vector<unsigned char> make_put_payload(
    std::uint64_t tx_id,
    const std::string& key,
    const std::string& value) {
    std::vector<unsigned char> payload;
    payload.reserve(1 + 8 + 4 + 4 + key.size() + value.size());
    payload.push_back(static_cast<unsigned char>(WalRecordType::Put));
    codec::append_u64(payload, tx_id);
    codec::append_u32(payload, static_cast<std::uint32_t>(key.size()));
    codec::append_u32(payload, static_cast<std::uint32_t>(value.size()));
    payload.insert(payload.end(), key.begin(), key.end());
    payload.insert(payload.end(), value.begin(), value.end());
    return payload;
}

std::vector<unsigned char> make_delete_payload(
    std::uint64_t tx_id,
    const std::string& key) {
    std::vector<unsigned char> payload;
    payload.reserve(1 + 8 + 4 + key.size());
    payload.push_back(static_cast<unsigned char>(WalRecordType::Delete));
    codec::append_u64(payload, tx_id);
    codec::append_u32(payload, static_cast<std::uint32_t>(key.size()));
    payload.insert(payload.end(), key.begin(), key.end());
    return payload;
}

std::vector<unsigned char> make_commit_payload(
    std::uint64_t tx_id,
    std::uint64_t sequence) {
    std::vector<unsigned char> payload;
    payload.reserve(17);
    payload.push_back(static_cast<unsigned char>(WalRecordType::Commit));
    codec::append_u64(payload, tx_id);
    codec::append_u64(payload, sequence);
    return payload;
}

}  // namespace

WalManager::WalManager(std::filesystem::path path) : path_(std::move(path)) {
    fd_ = ::open(path_.c_str(), O_CREAT | O_RDWR | O_APPEND | O_CLOEXEC, 0644);
    if (fd_ < 0) {
        throw std::runtime_error(codec::errno_message("cannot open WAL"));
    }
}

WalManager::~WalManager() {
    if (fd_ >= 0) {
        ::close(fd_);
    }
}

void WalManager::append_put(
    std::uint64_t tx_id,
    const std::string& key,
    const std::string& value) {
    append_record(make_put_payload(tx_id, key, value));
}

void WalManager::append_delete(
    std::uint64_t tx_id,
    const std::string& key) {
    append_record(make_delete_payload(tx_id, key));
}

void WalManager::append_commit(
    std::uint64_t tx_id,
    std::uint64_t sequence) {
    append_record(make_commit_payload(tx_id, sequence));
}

void WalManager::sync_commit() {
    codec::sync_fd(fd_, true, "WAL");
}

void WalManager::append_record(const std::vector<unsigned char>& payload) {
    if (payload.empty() || payload.size() > kMaxWalPayload) {
        throw std::runtime_error("WAL record payload is outside supported bounds");
    }

    std::vector<unsigned char> header;
    header.reserve(kWalHeaderSize);
    codec::append_u32(header, kWalMagic);
    codec::append_u32(header, static_cast<std::uint32_t>(payload.size()));
    codec::append_u32(header, codec::crc32(payload));

    if (!codec::write_all(fd_, header) || !codec::write_all(fd_, payload)) {
        throw std::runtime_error(codec::errno_message("cannot append WAL record"));
    }
}

RecoveryResult WalManager::recover(std::uint64_t snapshot_sequence) {
    const auto bytes = codec::read_file(path_);
    RecoveryResult result;
    std::map<std::uint64_t, OrderedValues> pending;
    std::size_t pos = 0;
    std::size_t valid_end = 0;
    std::uint64_t sequence = snapshot_sequence;

    while (pos < bytes.size()) {
        const std::size_t record_start = pos;
        if (bytes.size() - pos < kWalHeaderSize) {
            truncate_to(valid_end);
            result.truncated_torn_tail = true;
            break;
        }

        std::uint32_t magic = 0;
        std::uint32_t length = 0;
        std::uint32_t expected_crc = 0;
        if (!codec::read_u32(bytes, pos, magic) ||
            !codec::read_u32(bytes, pos, length) ||
            !codec::read_u32(bytes, pos, expected_crc)) {
            throw std::runtime_error("WAL corruption: invalid record header");
        }
        if (magic != kWalMagic || length == 0 || length > kMaxWalPayload) {
            truncate_to(valid_end);
            result.truncated_torn_tail = true;
            break;
        }
        if (bytes.size() - pos < length) {
            truncate_to(valid_end);
            result.truncated_torn_tail = true;
            break;
        }

        std::vector<unsigned char> payload(
            bytes.begin() + static_cast<std::ptrdiff_t>(pos),
            bytes.begin() + static_cast<std::ptrdiff_t>(pos + length));
        if (codec::crc32(payload) != expected_crc) {
            truncate_to(valid_end);
            result.truncated_torn_tail = true;
            break;
        }
        pos += length;
        valid_end = pos;

        if (payload.empty()) {
            throw std::runtime_error("WAL corruption: empty payload");
        }

        const auto type = static_cast<WalRecordType>(payload[0]);
        if (type == WalRecordType::Put || type == WalRecordType::Delete) {
            WalMutation mutation = parse_mutation(payload);
            result.max_tx_id = std::max(result.max_tx_id, mutation.tx_id);
            if (mutation.type == WalRecordType::Put) {
                pending[mutation.tx_id][mutation.key] = mutation.value;
            } else {
                pending[mutation.tx_id][mutation.key] = std::nullopt;
            }
            continue;
        }

        if (type == WalRecordType::Commit) {
            WalCommit commit = parse_commit(payload);
            result.max_tx_id = std::max(result.max_tx_id, commit.tx_id);
            auto pending_it = pending.find(commit.tx_id);
            OrderedValues writes;
            if (pending_it != pending.end()) {
                writes = std::move(pending_it->second);
                pending.erase(pending_it);
            }

            if (commit.sequence <= snapshot_sequence) {
                continue;
            }
            sequence = commit.sequence;
            result.commits.push_back(
                RecoveredCommit{commit.sequence, std::move(writes)});
            continue;
        }

        throw std::runtime_error("WAL corruption: unknown record type");
    }

    for (auto& [_, writes] : pending) {
        if (!writes.empty()) {
            ++sequence;
            result.commits.push_back(RecoveredCommit{sequence, std::move(writes)});
        }
    }
    return result;
}

void WalManager::reset_after_checkpoint() {
    codec::sync_fd(fd_, true, "checkpoint WAL");
}

std::uint64_t WalManager::size() const {
    return codec::file_size(fd_);
}

void WalManager::truncate_to(std::size_t valid_end) {
    if (::ftruncate(fd_, static_cast<off_t>(valid_end)) != 0) {
        throw std::runtime_error(codec::errno_message("cannot truncate torn WAL tail"));
    }
    codec::sync_fd(fd_, true, "repaired WAL");
}

WalMutation WalManager::parse_mutation(
    const std::vector<unsigned char>& payload) const {
    if (payload.empty()) {
        throw std::runtime_error("WAL corruption: empty mutation");
    }

    const auto type = static_cast<WalRecordType>(payload[0]);
    if (type != WalRecordType::Put && type != WalRecordType::Delete) {
        throw std::runtime_error("WAL corruption: invalid mutation type");
    }

    std::size_t pos = 1;
    std::uint64_t tx_id = 0;
    std::uint32_t key_len = 0;
    std::uint32_t value_len = 0;

    if (!codec::read_u64(payload, pos, tx_id)) {
        throw std::runtime_error("WAL corruption: missing transaction id");
    }
    if (!codec::read_u32(payload, pos, key_len) || key_len > kMaxKeyBytes) {
        throw std::runtime_error("WAL corruption: invalid key length");
    }
    if (type == WalRecordType::Put) {
        if (!codec::read_u32(payload, pos, value_len) ||
            value_len > kMaxValueBytes) {
            throw std::runtime_error("WAL corruption: invalid value length");
        }
    }

    const std::size_t expected =
        static_cast<std::size_t>(key_len) +
        (type == WalRecordType::Put ? static_cast<std::size_t>(value_len) : 0U);
    if (pos > payload.size() || payload.size() - pos != expected) {
        throw std::runtime_error("WAL corruption: malformed mutation");
    }

    WalMutation mutation;
    mutation.type = type;
    mutation.tx_id = tx_id;
    mutation.key.assign(
        reinterpret_cast<const char*>(payload.data() + pos),
        key_len);
    pos += key_len;

    if (type == WalRecordType::Put) {
        mutation.value.assign(
            reinterpret_cast<const char*>(payload.data() + pos),
            value_len);
    }
    return mutation;
}

WalCommit WalManager::parse_commit(
    const std::vector<unsigned char>& payload) const {
    std::size_t pos = 1;
    WalCommit commit;
    if (!codec::read_u64(payload, pos, commit.tx_id) ||
        !codec::read_u64(payload, pos, commit.sequence) ||
        pos != payload.size()) {
        throw std::runtime_error("WAL corruption: malformed commit");
    }
    return commit;
}

}  // namespace stonevault
