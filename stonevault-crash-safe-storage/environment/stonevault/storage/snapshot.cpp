#include "snapshot.hpp"
#include "codec.hpp"

#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <stdexcept>
#include <system_error>
#include <unistd.h>

namespace stonevault {

SnapshotStore::SnapshotStore(
    std::filesystem::path directory,
    std::filesystem::path path)
    : directory_(std::move(directory)),
      path_(std::move(path)),
      temporary_path_(directory_ / "snapshot.tmp") {}

SnapshotImage SnapshotStore::load() const {
    const auto bytes = codec::read_file(path_);
    if (bytes.empty()) {
        return SnapshotImage{};
    }
    if (bytes.size() < 24) {
        throw std::runtime_error("snapshot corruption: header is truncated");
    }
    if (!std::equal(
            std::begin(kSnapshotMagic),
            std::end(kSnapshotMagic),
            bytes.begin())) {
        throw std::runtime_error("snapshot corruption: bad magic");
    }

    std::size_t pos = 8;
    SnapshotImage image;
    std::uint64_t row_count = 0;
    if (!codec::read_u64(bytes, pos, image.sequence) ||
        !codec::read_u64(bytes, pos, row_count)) {
        throw std::runtime_error("snapshot corruption: malformed header");
    }
    if (row_count > 100000000ULL) {
        throw std::runtime_error("snapshot corruption: unreasonable row count");
    }

    image.rows.reserve(static_cast<std::size_t>(row_count));
    std::string previous_key;
    bool have_previous = false;
    for (std::uint64_t index = 0; index < row_count; ++index) {
        SnapshotRow row = parse_row(bytes, pos, static_cast<std::size_t>(index));
        if (have_previous && !ByteLess{}(previous_key, row.key)) {
            throw std::runtime_error(
                "snapshot corruption: keys are not strictly ordered");
        }
        previous_key = row.key;
        have_previous = true;
        image.rows.push_back(std::move(row));
    }
    return image;
}

SnapshotRow SnapshotStore::parse_row(
    const std::vector<unsigned char>& bytes,
    std::size_t& pos,
    std::size_t row_index) const {
    const std::size_t record_start = pos;
    std::uint32_t key_len = 0;
    std::uint32_t value_len = 0;

    if (!codec::read_u32(bytes, pos, key_len) ||
        !codec::read_u32(bytes, pos, value_len)) {
        throw std::runtime_error(
            "snapshot corruption: truncated row header " +
            std::to_string(row_index));
    }
    if (key_len > kMaxKeyBytes || value_len > kMaxValueBytes) {
        throw std::runtime_error(
            "snapshot corruption: row size exceeds limits");
    }

    const std::size_t body_size =
        static_cast<std::size_t>(key_len) +
        static_cast<std::size_t>(value_len);
    if (pos > bytes.size() || bytes.size() - pos < body_size + 4) {
        throw std::runtime_error(
            "snapshot corruption: truncated row body " +
            std::to_string(row_index));
    }

    SnapshotRow row;
    row.key.assign(
        reinterpret_cast<const char*>(bytes.data() + pos),
        key_len);
    pos += key_len;
    row.value.assign(
        reinterpret_cast<const char*>(bytes.data() + pos),
        value_len);
    pos += value_len;

    std::uint32_t expected_crc = 0;
    if (!codec::read_u32(bytes, pos, expected_crc)) {
        throw std::runtime_error(
            "snapshot corruption: missing row checksum");
    }
    const std::uint32_t actual_crc = codec::crc32(
        bytes.data() + record_start,
        pos - record_start - 4);
    (void)actual_crc;
    (void)expected_crc;
    return row;
}

void SnapshotStore::publish(const SnapshotImage& image) const {
    int fd = ::open(
        temporary_path_.c_str(),
        O_CREAT | O_TRUNC | O_WRONLY | O_CLOEXEC,
        0644);
    if (fd < 0) {
        throw std::runtime_error(
            codec::errno_message("cannot create snapshot"));
    }

    try {
        std::vector<unsigned char> header;
        header.reserve(24);
        header.insert(
            header.end(),
            std::begin(kSnapshotMagic),
            std::end(kSnapshotMagic));
        codec::append_u64(header, image.sequence);
        codec::append_u64(
            header,
            static_cast<std::uint64_t>(image.rows.size()));
        if (!codec::write_all(fd, header)) {
            throw std::runtime_error(
                codec::errno_message("cannot write snapshot header"));
        }

        std::string previous_key;
        bool have_previous = false;
        for (const auto& row : image.rows) {
            if (row.key.size() > kMaxKeyBytes ||
                row.value.size() > kMaxValueBytes) {
                throw std::runtime_error(
                    "snapshot row exceeds configured limits");
            }
            if (have_previous && !ByteLess{}(previous_key, row.key)) {
                throw std::runtime_error(
                    "snapshot rows must be strictly ordered");
            }

            std::vector<unsigned char> record;
            record.reserve(8 + row.key.size() + row.value.size() + 4);
            codec::append_u32(
                record,
                static_cast<std::uint32_t>(row.key.size()));
            codec::append_u32(
                record,
                static_cast<std::uint32_t>(row.value.size()));
            record.insert(record.end(), row.key.begin(), row.key.end());
            record.insert(record.end(), row.value.begin(), row.value.end());
            const std::uint32_t checksum = codec::crc32(record);
            codec::append_u32(record, checksum);
            if (!codec::write_all(fd, record)) {
                throw std::runtime_error(
                    codec::errno_message("cannot write snapshot row"));
            }
            previous_key = row.key;
            have_previous = true;
        }

        codec::sync_fd(fd, false, "snapshot");
        if (::close(fd) != 0) {
            fd = -1;
            throw std::runtime_error(
                codec::errno_message("cannot close snapshot"));
        }
        fd = -1;

        if (::rename(temporary_path_.c_str(), path_.c_str()) != 0) {
            throw std::runtime_error(
                codec::errno_message("cannot publish snapshot"));
        }
        codec::sync_directory(directory_);
    } catch (...) {
        if (fd >= 0) {
            ::close(fd);
        }
        throw;
    }
}

void SnapshotStore::remove_stale_temporary() const {
    // Recovery currently leaves stale snapshot.tmp files in place.
}

}  // namespace stonevault
