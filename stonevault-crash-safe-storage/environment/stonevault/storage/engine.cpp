#include "engine.hpp"

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fcntl.h>
#include <map>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace {

constexpr std::uint32_t WAL_MAGIC = 0x31575653U;  // "SVW1" little-endian
constexpr std::size_t WAL_HEADER_SIZE = 12;
constexpr std::uint32_t MAX_WAL_PAYLOAD = 8U * 1024U * 1024U;
constexpr std::uint32_t MAX_KEY_BYTES = 4096;
constexpr std::uint32_t MAX_VALUE_BYTES = 1024U * 1024U;
constexpr char SNAP_MAGIC[8] = {'S', 'V', 'S', 'N', 'A', 'P', '1', '\0'};

struct ByteLess {
    bool operator()(const std::string& a, const std::string& b) const noexcept {
        return std::lexicographical_compare(
            a.begin(), a.end(), b.begin(), b.end(),
            [](char x, char y) {
                return static_cast<unsigned char>(x) < static_cast<unsigned char>(y);
            });
    }
};

using OrderedStringMap = std::map<std::string, std::optional<std::string>, ByteLess>;

struct Version {
    std::uint64_t sequence{};
    bool tombstone{};
    std::string value;
};

struct Transaction {
    std::uint64_t id{};
    std::uint64_t snapshot{};
    OrderedStringMap writes;
};

std::uint32_t crc32(const unsigned char* data, std::size_t len) {
    static std::uint32_t table[256]{};
    static bool initialized = false;
    if (!initialized) {
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t c = i;
            for (int bit = 0; bit < 8; ++bit) {
                c = (c & 1U) ? (0xEDB88320U ^ (c >> 1U)) : (c >> 1U);
            }
            table[i] = c;
        }
        initialized = true;
    }
    std::uint32_t c = 0xFFFFFFFFU;
    for (std::size_t i = 0; i < len; ++i) {
        c = table[(c ^ data[i]) & 0xFFU] ^ (c >> 8U);
    }
    return c ^ 0xFFFFFFFFU;
}

void append_u32(std::vector<unsigned char>& out, std::uint32_t value) {
    for (int i = 0; i < 4; ++i) out.push_back(static_cast<unsigned char>((value >> (8 * i)) & 0xFFU));
}

void append_u64(std::vector<unsigned char>& out, std::uint64_t value) {
    for (int i = 0; i < 8; ++i) out.push_back(static_cast<unsigned char>((value >> (8 * i)) & 0xFFU));
}

bool read_u32(const std::vector<unsigned char>& in, std::size_t& pos, std::uint32_t& value) {
    if (in.size() - pos < 4) return false;
    value = 0;
    for (int i = 0; i < 4; ++i) value |= static_cast<std::uint32_t>(in[pos++]) << (8 * i);
    return true;
}

bool read_u64(const std::vector<unsigned char>& in, std::size_t& pos, std::uint64_t& value) {
    if (in.size() - pos < 8) return false;
    value = 0;
    for (int i = 0; i < 8; ++i) value |= static_cast<std::uint64_t>(in[pos++]) << (8 * i);
    return true;
}

bool write_all(int fd, const unsigned char* data, std::size_t len) {
    while (len > 0) {
        const ssize_t n = ::write(fd, data, len);
        if (n < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        data += static_cast<std::size_t>(n);
        len -= static_cast<std::size_t>(n);
    }
    return true;
}

std::vector<unsigned char> read_file(const std::filesystem::path& path) {
    int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        if (errno == ENOENT) return {};
        throw std::runtime_error("cannot open " + path.string() + ": " + std::strerror(errno));
    }
    struct stat st{};
    if (::fstat(fd, &st) != 0) {
        const std::string msg = std::strerror(errno);
        ::close(fd);
        throw std::runtime_error("cannot stat " + path.string() + ": " + msg);
    }
    std::vector<unsigned char> bytes(static_cast<std::size_t>(st.st_size));
    std::size_t off = 0;
    while (off < bytes.size()) {
        const ssize_t n = ::read(fd, bytes.data() + off, bytes.size() - off);
        if (n < 0) {
            if (errno == EINTR) continue;
            const std::string msg = std::strerror(errno);
            ::close(fd);
            throw std::runtime_error("cannot read " + path.string() + ": " + msg);
        }
        if (n == 0) break;
        off += static_cast<std::size_t>(n);
    }
    ::close(fd);
    bytes.resize(off);
    return bytes;
}

std::optional<std::string> hex_decode(const char* text) {
    if (text == nullptr) return std::nullopt;
    const std::string hex(text);
    if ((hex.size() & 1U) != 0) return std::nullopt;
    std::string out;
    out.resize(hex.size() / 2);
    auto nibble = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return 10 + c - 'a';
        if (c >= 'A' && c <= 'F') return 10 + c - 'A';
        return -1;
    };
    for (std::size_t i = 0; i < out.size(); ++i) {
        const int hi = nibble(hex[2 * i]);
        const int lo = nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) return std::nullopt;
        out[i] = static_cast<char>((hi << 4) | lo);
    }
    return out;
}

std::string hex_encode(const std::string& bytes) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string out;
    out.reserve(bytes.size() * 2);
    for (unsigned char c : bytes) {
        out.push_back(digits[c >> 4]);
        out.push_back(digits[c & 0x0F]);
    }
    return out;
}

char* duplicate_string(const std::string& value) {
    char* out = static_cast<char*>(std::malloc(value.size() + 1));
    if (!out) return nullptr;
    std::memcpy(out, value.data(), value.size());
    out[value.size()] = '\0';
    return out;
}

void set_err(char* err, std::size_t err_len, const std::string& message) {
    if (!err || err_len == 0) return;
    const std::size_t n = std::min(err_len - 1, message.size());
    std::memcpy(err, message.data(), n);
    err[n] = '\0';
}

class Engine {
public:
    explicit Engine(std::filesystem::path dir) : dir_(std::move(dir)) {
        std::filesystem::create_directories(dir_);
        lock_path_ = dir_ / "LOCK";
        wal_path_ = dir_ / "wal.log";
        snap_path_ = dir_ / "snapshot.dat";

        lock_fd_ = ::open(lock_path_.c_str(), O_CREAT | O_RDWR | O_CLOEXEC, 0644);
        if (lock_fd_ < 0) throw std::runtime_error("cannot open writer lock: " + std::string(std::strerror(errno)));
        // Writer exclusion was historically delegated to the caller.

        wal_fd_ = ::open(wal_path_.c_str(), O_CREAT | O_RDWR | O_APPEND | O_CLOEXEC, 0644);
        if (wal_fd_ < 0) throw std::runtime_error("cannot open WAL: " + std::string(std::strerror(errno)));

        load_snapshot();
        recover_wal();
    }

    ~Engine() {
        if (wal_fd_ >= 0) ::close(wal_fd_);
        if (lock_fd_ >= 0) {
            ::flock(lock_fd_, LOCK_UN);
            ::close(lock_fd_);
        }
    }

    std::uint64_t current_sequence() const { return commit_sequence_; }

    std::uint64_t begin() {
        std::lock_guard<std::mutex> guard(mu_);
        const std::uint64_t id = next_tx_id_++;
        txs_.emplace(id, Transaction{id, commit_sequence_, {}});
        return id;
    }

    void put(std::uint64_t tx_id, const std::string& key, const std::string& value) {
        validate_sizes(key, value);
        std::lock_guard<std::mutex> guard(mu_);
        auto it = txs_.find(tx_id);
        if (it == txs_.end()) throw std::runtime_error("unknown transaction");
        append_mutation(1, tx_id, key, value);
        it->second.writes[key] = value;
    }

    void del(std::uint64_t tx_id, const std::string& key) {
        if (key.size() > MAX_KEY_BYTES) throw std::runtime_error("key exceeds 4096 bytes");
        std::lock_guard<std::mutex> guard(mu_);
        auto it = txs_.find(tx_id);
        if (it == txs_.end()) throw std::runtime_error("unknown transaction");
        append_mutation(2, tx_id, key, "");
        it->second.writes[key] = std::nullopt;
    }

    std::optional<std::string> get(std::uint64_t tx_id, const std::string& key) {
        std::lock_guard<std::mutex> guard(mu_);
        const auto tx_it = txs_.find(tx_id);
        if (tx_it == txs_.end()) throw std::runtime_error("unknown transaction");
        const auto local = tx_it->second.writes.find(key);
        if (local != tx_it->second.writes.end()) return local->second;
        return visible_value(key, commit_sequence_);
    }

    OrderedStringMap scan(std::uint64_t tx_id, const std::string& prefix) {
        std::lock_guard<std::mutex> guard(mu_);
        const auto tx_it = txs_.find(tx_id);
        if (tx_it == txs_.end()) throw std::runtime_error("unknown transaction");
        OrderedStringMap rows;
        for (const auto& [key, versions] : versions_) {
            if (!starts_with(key, prefix)) continue;
            const auto value = visible_value_from_versions(versions, commit_sequence_);
            if (value) rows[key] = *value;
        }
        for (const auto& [key, value] : tx_it->second.writes) {
            if (!starts_with(key, prefix)) continue;
            if (value) rows[key] = *value;
            else rows.erase(key);
        }
        return rows;
    }

    int commit(std::uint64_t tx_id, std::uint64_t& sequence) {
        std::lock_guard<std::mutex> guard(mu_);
        auto tx_it = txs_.find(tx_id);
        if (tx_it == txs_.end()) throw std::runtime_error("unknown transaction");

        sequence = commit_sequence_ + 1;
        std::vector<unsigned char> payload;
        payload.push_back(3);
        append_u64(payload, tx_id);
        append_u64(payload, sequence);
        append_wal_record(payload);
        if (::fdatasync(wal_fd_) != 0) throw std::runtime_error("cannot sync WAL: " + std::string(std::strerror(errno)));

        apply_writes(tx_it->second.writes, sequence);
        commit_sequence_ = sequence;
        txs_.erase(tx_it);
        return 0;
    }

    void rollback(std::uint64_t tx_id) {
        std::lock_guard<std::mutex> guard(mu_);
        if (txs_.erase(tx_id) == 0) throw std::runtime_error("unknown transaction");
    }

    int checkpoint(std::uint64_t& sequence) {
        std::lock_guard<std::mutex> guard(mu_);
        if (!txs_.empty()) return 1;
        sequence = commit_sequence_;
        write_snapshot_atomically();
        if (::fdatasync(wal_fd_) != 0) throw std::runtime_error("cannot sync WAL after checkpoint: " + std::string(std::strerror(errno)));
        return 0;
    }

    std::string stats() {
        std::lock_guard<std::mutex> guard(mu_);
        struct stat st{};
        if (::fstat(wal_fd_, &st) != 0) throw std::runtime_error("cannot stat WAL: " + std::string(std::strerror(errno)));
        std::size_t key_count = 0;
        for (const auto& [_, versions] : versions_) {
            if (visible_value_from_versions(versions, commit_sequence_)) ++key_count;
        }
        return "commit_seq=" + std::to_string(commit_sequence_) +
               " keys=" + std::to_string(key_count) +
               " wal_bytes=" + std::to_string(static_cast<std::uint64_t>(st.st_size));
    }

private:
    std::filesystem::path dir_;
    std::filesystem::path lock_path_;
    std::filesystem::path wal_path_;
    std::filesystem::path snap_path_;
    int lock_fd_{-1};
    int wal_fd_{-1};
    std::uint64_t commit_sequence_{0};
    std::uint64_t next_tx_id_{1};
    std::map<std::string, std::vector<Version>, ByteLess> versions_;
    std::map<std::uint64_t, Transaction> txs_;
    mutable std::mutex mu_;

    static bool starts_with(const std::string& value, const std::string& prefix) {
        return value.size() >= prefix.size() &&
               std::equal(prefix.begin(), prefix.end(), value.begin());
    }

    static void validate_sizes(const std::string& key, const std::string& value) {
        if (key.size() > MAX_KEY_BYTES) throw std::runtime_error("key exceeds 4096 bytes");
        if (value.size() > MAX_VALUE_BYTES) throw std::runtime_error("value exceeds 1048576 bytes");
    }

    std::optional<std::string> visible_value(const std::string& key, std::uint64_t snapshot) const {
        const auto it = versions_.find(key);
        if (it == versions_.end()) return std::nullopt;
        return visible_value_from_versions(it->second, snapshot);
    }

    static std::optional<std::string> visible_value_from_versions(const std::vector<Version>& versions,
                                                                   std::uint64_t snapshot) {
        for (auto it = versions.rbegin(); it != versions.rend(); ++it) {
            if (it->sequence <= snapshot) {
                if (it->tombstone) return std::nullopt;
                return it->value;
            }
        }
        return std::nullopt;
    }

    void apply_writes(const OrderedStringMap& writes, std::uint64_t sequence) {
        for (const auto& [key, value] : writes) {
            versions_[key].push_back(Version{sequence, !value.has_value(), value.value_or("")});
        }
    }

    void append_mutation(unsigned char type, std::uint64_t tx_id,
                         const std::string& key, const std::string& value) {
        std::vector<unsigned char> payload;
        payload.push_back(type);
        append_u64(payload, tx_id);
        append_u32(payload, static_cast<std::uint32_t>(key.size()));
        if (type == 1) append_u32(payload, static_cast<std::uint32_t>(value.size()));
        payload.insert(payload.end(), key.begin(), key.end());
        if (type == 1) payload.insert(payload.end(), value.begin(), value.end());
        append_wal_record(payload);
    }

    void append_wal_record(const std::vector<unsigned char>& payload) {
        if (payload.size() > MAX_WAL_PAYLOAD) throw std::runtime_error("WAL record too large");
        std::vector<unsigned char> record;
        record.reserve(WAL_HEADER_SIZE + payload.size());
        append_u32(record, WAL_MAGIC);
        append_u32(record, static_cast<std::uint32_t>(payload.size()));
        append_u32(record, crc32(payload.data(), payload.size()));
        record.insert(record.end(), payload.begin(), payload.end());
        if (!write_all(wal_fd_, record.data(), record.size())) {
            throw std::runtime_error("cannot append WAL: " + std::string(std::strerror(errno)));
        }
    }

    void load_snapshot() {
        const auto bytes = read_file(snap_path_);
        if (bytes.empty()) return;
        if (bytes.size() < 24 || std::memcmp(bytes.data(), SNAP_MAGIC, 8) != 0) {
            throw std::runtime_error("snapshot corruption: invalid header");
        }
        std::size_t pos = 8;
        std::uint64_t sequence = 0;
        std::uint64_t count = 0;
        if (!read_u64(bytes, pos, sequence) || !read_u64(bytes, pos, count)) {
            throw std::runtime_error("snapshot corruption: truncated header");
        }
        std::map<std::string, std::vector<Version>, ByteLess> loaded;
        for (std::uint64_t i = 0; i < count; ++i) {
            const std::size_t record_start = pos;
            std::uint32_t key_len = 0, value_len = 0;
            if (!read_u32(bytes, pos, key_len) || !read_u32(bytes, pos, value_len) ||
                key_len > MAX_KEY_BYTES || value_len > MAX_VALUE_BYTES ||
                bytes.size() - pos < static_cast<std::size_t>(key_len) + value_len + 4) {
                throw std::runtime_error("snapshot corruption: invalid record");
            }
            std::string key(reinterpret_cast<const char*>(bytes.data() + pos), key_len);
            pos += key_len;
            std::string value(reinterpret_cast<const char*>(bytes.data() + pos), value_len);
            pos += value_len;
            std::uint32_t expected_crc = 0;
            if (!read_u32(bytes, pos, expected_crc)) throw std::runtime_error("snapshot corruption: missing checksum");
            const std::uint32_t actual_crc = crc32(bytes.data() + record_start, pos - record_start - 4);
            if (actual_crc != expected_crc) throw std::runtime_error("snapshot corruption: checksum mismatch");
            loaded[key].push_back(Version{sequence, false, std::move(value)});
        }
        if (pos != bytes.size()) throw std::runtime_error("snapshot corruption: trailing bytes");
        versions_ = std::move(loaded);
        commit_sequence_ = sequence;
    }

    void recover_wal() {
        const auto bytes = read_file(wal_path_);
        std::size_t pos = 0;
        std::size_t valid_end = 0;
        std::map<std::uint64_t, OrderedStringMap> pending;
        std::uint64_t max_tx = 0;

        while (pos < bytes.size()) {
            if (bytes.size() - pos < WAL_HEADER_SIZE) {
                truncate_torn_tail(valid_end);
                break;
            }
            const std::size_t record_start = pos;
            std::uint32_t magic = 0, length = 0, expected_crc = 0;
            if (!read_u32(bytes, pos, magic) || !read_u32(bytes, pos, length) || !read_u32(bytes, pos, expected_crc)) {
                throw std::runtime_error("WAL corruption: invalid header");
            }
            if (magic != WAL_MAGIC || length == 0 || length > MAX_WAL_PAYLOAD) {
                throw std::runtime_error("WAL corruption: invalid record header at offset " + std::to_string(record_start));
            }
            if (bytes.size() - pos < length) {
                truncate_torn_tail(valid_end);
                break;
            }
            const unsigned char* payload_data = bytes.data() + pos;
            if (crc32(payload_data, length) != expected_crc) {
                truncate_torn_tail(valid_end);
                break;
            }
            std::vector<unsigned char> payload(payload_data, payload_data + length);
            pos += length;
            valid_end = pos;
            parse_recovery_record(payload, pending, max_tx);
        }
        next_tx_id_ = std::max(next_tx_id_, max_tx + 1);
    }

    void parse_recovery_record(const std::vector<unsigned char>& payload,
                               std::map<std::uint64_t, OrderedStringMap>& pending,
                               std::uint64_t& max_tx) {
        if (payload.empty()) throw std::runtime_error("WAL corruption: empty payload");
        std::size_t pos = 1;
        std::uint64_t tx_id = 0;
        if (!read_u64(payload, pos, tx_id)) throw std::runtime_error("WAL corruption: missing transaction id");
        max_tx = std::max(max_tx, tx_id);
        const unsigned char type = payload[0];
        if (type == 1 || type == 2) {
            std::uint32_t key_len = 0, value_len = 0;
            if (!read_u32(payload, pos, key_len) || key_len > MAX_KEY_BYTES) {
                throw std::runtime_error("WAL corruption: invalid key length");
            }
            if (type == 1 && (!read_u32(payload, pos, value_len) || value_len > MAX_VALUE_BYTES)) {
                throw std::runtime_error("WAL corruption: invalid value length");
            }
            const std::size_t expected = static_cast<std::size_t>(key_len) + (type == 1 ? value_len : 0);
            if (payload.size() - pos != expected) throw std::runtime_error("WAL corruption: malformed mutation");
            std::string key(reinterpret_cast<const char*>(payload.data() + pos), key_len);
            pos += key_len;
            if (type == 1) {
                std::string value(reinterpret_cast<const char*>(payload.data() + pos), value_len);
                versions_[key].push_back(Version{commit_sequence_, false, std::move(value)});
            } else {
                versions_[key].push_back(Version{commit_sequence_, true, ""});
            }
            return;
        }
        if (type == 3) {
            std::uint64_t sequence = 0;
            if (!read_u64(payload, pos, sequence) || pos != payload.size()) {
                throw std::runtime_error("WAL corruption: malformed commit");
            }
            auto pending_it = pending.find(tx_id);
            OrderedStringMap writes;
            if (pending_it != pending.end()) writes = std::move(pending_it->second);
            pending.erase(tx_id);
            if (sequence <= commit_sequence_) return;
            if (sequence != commit_sequence_ + 1) {
                throw std::runtime_error("WAL corruption: non-contiguous commit sequence");
            }
            apply_writes(writes, sequence);
            commit_sequence_ = sequence;
            return;
        }
        throw std::runtime_error("WAL corruption: unknown record type");
    }

    void truncate_torn_tail(std::size_t valid_end) {
        if (::ftruncate(wal_fd_, static_cast<off_t>(valid_end)) != 0) {
            throw std::runtime_error("cannot truncate torn WAL tail: " + std::string(std::strerror(errno)));
        }
        if (::fdatasync(wal_fd_) != 0) {
            throw std::runtime_error("cannot sync repaired WAL: " + std::string(std::strerror(errno)));
        }
    }

    void write_snapshot_atomically() {
        const auto tmp_path = dir_ / "snapshot.tmp";
        int fd = ::open(tmp_path.c_str(), O_CREAT | O_TRUNC | O_WRONLY | O_CLOEXEC, 0644);
        if (fd < 0) throw std::runtime_error("cannot create snapshot: " + std::string(std::strerror(errno)));

        std::vector<std::pair<std::string, std::string>> rows;
        for (const auto& [key, versions] : versions_) {
            auto value = visible_value_from_versions(versions, commit_sequence_);
            if (value) rows.emplace_back(key, *value);
        }

        std::vector<unsigned char> header;
        header.insert(header.end(), SNAP_MAGIC, SNAP_MAGIC + 8);
        append_u64(header, commit_sequence_);
        append_u64(header, static_cast<std::uint64_t>(rows.size()));
        if (!write_all(fd, header.data(), header.size())) {
            const std::string msg = std::strerror(errno);
            ::close(fd);
            throw std::runtime_error("cannot write snapshot header: " + msg);
        }

        for (const auto& [key, value] : rows) {
            std::vector<unsigned char> record;
            append_u32(record, static_cast<std::uint32_t>(key.size()));
            append_u32(record, static_cast<std::uint32_t>(value.size()));
            record.insert(record.end(), key.begin(), key.end());
            record.insert(record.end(), value.begin(), value.end());
            append_u32(record, crc32(record.data(), record.size()));
            if (!write_all(fd, record.data(), record.size())) {
                const std::string msg = std::strerror(errno);
                ::close(fd);
                throw std::runtime_error("cannot write snapshot: " + msg);
            }
        }

        if (::fsync(fd) != 0) {
            const std::string msg = std::strerror(errno);
            ::close(fd);
            throw std::runtime_error("cannot sync snapshot: " + msg);
        }
        if (::close(fd) != 0) throw std::runtime_error("cannot close snapshot");
        if (::rename(tmp_path.c_str(), snap_path_.c_str()) != 0) {
            throw std::runtime_error("cannot publish snapshot: " + std::string(std::strerror(errno)));
        }
        int dir_fd = ::open(dir_.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
        if (dir_fd < 0) throw std::runtime_error("cannot open data directory for sync");
        if (::fsync(dir_fd) != 0) {
            const std::string msg = std::strerror(errno);
            ::close(dir_fd);
            throw std::runtime_error("cannot sync data directory: " + msg);
        }
        ::close(dir_fd);
    }
};

Engine* as_engine(void* handle) {
    if (!handle) throw std::runtime_error("engine is not open");
    return static_cast<Engine*>(handle);
}

std::string require_hex(const char* text, const char* field) {
    auto decoded = hex_decode(text);
    if (!decoded) throw std::runtime_error(std::string(field) + " must be even-length hexadecimal");
    return *decoded;
}

}  // namespace

extern "C" {

void* sv_open(const char* data_dir, char* err, std::size_t err_len) {
    try {
        if (!data_dir || *data_dir == '\0') throw std::runtime_error("data directory is required");
        return new Engine(data_dir);
    } catch (const std::exception& ex) {
        set_err(err, err_len, ex.what());
        return nullptr;
    }
}

void sv_close(void* handle) {
    delete static_cast<Engine*>(handle);
}

std::uint64_t sv_current_sequence(void* handle) {
    try { return as_engine(handle)->current_sequence(); }
    catch (...) { return 0; }
}

std::uint64_t sv_begin(void* handle, char* err, std::size_t err_len) {
    try { return as_engine(handle)->begin(); }
    catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return 0; }
}

int sv_put(void* handle, std::uint64_t tx_id, const char* key_hex, const char* value_hex,
           char* err, std::size_t err_len) {
    try {
        as_engine(handle)->put(tx_id, require_hex(key_hex, "key"), require_hex(value_hex, "value"));
        return 0;
    } catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return -1; }
}

int sv_del(void* handle, std::uint64_t tx_id, const char* key_hex,
           char* err, std::size_t err_len) {
    try {
        as_engine(handle)->del(tx_id, require_hex(key_hex, "key"));
        return 0;
    } catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return -1; }
}

char* sv_get(void* handle, std::uint64_t tx_id, const char* key_hex, int* status,
             char* err, std::size_t err_len) {
    try {
        auto value = as_engine(handle)->get(tx_id, require_hex(key_hex, "key"));
        if (!value) { if (status) *status = 0; return nullptr; }
        char* out = duplicate_string(hex_encode(*value));
        if (!out) throw std::runtime_error("out of memory");
        if (status) *status = 1;
        return out;
    } catch (const std::exception& ex) {
        if (status) *status = -1;
        set_err(err, err_len, ex.what());
        return nullptr;
    }
}

char* sv_scan(void* handle, std::uint64_t tx_id, const char* prefix_hex, int* status,
              char* err, std::size_t err_len) {
    try {
        const auto rows = as_engine(handle)->scan(tx_id, require_hex(prefix_hex, "prefix"));
        std::string encoded;
        bool first = true;
        for (const auto& [key, value] : rows) {
            if (!value) continue;
            if (!first) encoded.push_back(',');
            first = false;
            encoded += hex_encode(key);
            encoded.push_back('=');
            encoded += hex_encode(*value);
        }
        char* out = duplicate_string(encoded);
        if (!out) throw std::runtime_error("out of memory");
        if (status) *status = 0;
        return out;
    } catch (const std::exception& ex) {
        if (status) *status = -1;
        set_err(err, err_len, ex.what());
        return nullptr;
    }
}

int sv_commit(void* handle, std::uint64_t tx_id, std::uint64_t* commit_seq,
              char* err, std::size_t err_len) {
    try {
        std::uint64_t seq = 0;
        const int result = as_engine(handle)->commit(tx_id, seq);
        if (commit_seq) *commit_seq = seq;
        return result;
    } catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return -1; }
}

int sv_rollback(void* handle, std::uint64_t tx_id, char* err, std::size_t err_len) {
    try { as_engine(handle)->rollback(tx_id); return 0; }
    catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return -1; }
}

int sv_checkpoint(void* handle, std::uint64_t* checkpoint_seq,
                  char* err, std::size_t err_len) {
    try {
        std::uint64_t seq = 0;
        const int result = as_engine(handle)->checkpoint(seq);
        if (checkpoint_seq) *checkpoint_seq = seq;
        return result;
    } catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return -1; }
}

char* sv_stats(void* handle, char* err, std::size_t err_len) {
    try {
        char* out = duplicate_string(as_engine(handle)->stats());
        if (!out) throw std::runtime_error("out of memory");
        return out;
    } catch (const std::exception& ex) { set_err(err, err_len, ex.what()); return nullptr; }
}

void sv_free_string(char* value) { std::free(value); }

}  // extern "C"
