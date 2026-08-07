#include "guardian/journal.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstddef>
#include <cstring>
#include <fcntl.h>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace guardian {
namespace {

constexpr std::uint32_t kMagic = 0x4752444eU;
constexpr std::uint16_t kVersion = 1;
constexpr std::size_t kTypeSize = 24;
constexpr std::size_t kUnitSize = 48;
constexpr std::size_t kDetailSize = 96;

#pragma pack(push, 1)
struct DiskRecord {
  std::uint32_t magic;
  std::uint16_t version;
  std::uint16_t record_size;
  std::uint64_t sequence;
  std::int64_t pid;
  std::array<char, kTypeSize> type;
  std::array<char, kUnitSize> unit;
  std::array<char, kDetailSize> detail;
  std::uint32_t checksum;
};
#pragma pack(pop)

static_assert(sizeof(DiskRecord) == 196);

template <std::size_t Size>
void store_text(std::array<char, Size>& target, std::string_view source) {
  if (source.size() >= Size) {
    throw Error("journal token too long");
  }
  target.fill('\0');
  std::copy(source.begin(), source.end(), target.begin());
}

template <std::size_t Size>
std::string load_text(const std::array<char, Size>& source) {
  const auto end = std::find(source.begin(), source.end(), '\0');
  if (end == source.end()) {
    throw Error("unterminated journal token");
  }
  return std::string(source.begin(), end);
}

std::uint32_t record_checksum(const DiskRecord& record) {
  const auto* begin = reinterpret_cast<const std::byte*>(&record);
  constexpr std::size_t checked = offsetof(DiskRecord, checksum);
  return crc32(std::span<const std::byte>(begin, checked));
}

DiskRecord encode(const Event& event) {
  DiskRecord record{};
  record.magic = kMagic;
  record.version = kVersion;
  record.record_size = static_cast<std::uint16_t>(sizeof(DiskRecord));
  record.sequence = event.sequence;
  record.pid = event.pid;
  store_text(record.type, event.type);
  store_text(record.unit, event.unit);
  store_text(record.detail, event.detail);
  record.checksum = record_checksum(record);
  return record;
}

Event decode(const DiskRecord& record) {
  Event event;
  event.sequence = record.sequence;
  event.pid = record.pid;
  event.type = load_text(record.type);
  event.unit = load_text(record.unit);
  event.detail = load_text(record.detail);
  return event;
}

bool record_header_valid(const DiskRecord& record) {
  return record.magic == kMagic && record.version == kVersion &&
         record.record_size == sizeof(DiskRecord);
}

ssize_t pread_retry(int fd, void* buffer, std::size_t size, off_t offset) {
  while (true) {
    const ssize_t count = ::pread(fd, buffer, size, offset);
    if (count < 0 && errno == EINTR) {
      continue;
    }
    return count;
  }
}

}  // namespace

Journal::Journal(const std::filesystem::path& path) : path_(path) {
  fd_.reset(::open(path.c_str(), O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW,
                   0600));
  if (!fd_.valid()) {
    throw Error(errno_message("open journal"));
  }
  recover();
}

void Journal::recover() {
  struct stat metadata {};
  if (::fstat(fd_.get(), &metadata) < 0) {
    throw Error(errno_message("stat journal"));
  }
  off_t offset = 0;
  std::uint64_t expected = 1;
  bool tail_found = false;
  while (offset < metadata.st_size) {
    DiskRecord record{};
    const ssize_t count = pread_retry(fd_.get(), &record, sizeof(record), offset);
    if (count < 0) {
      throw Error(errno_message("read journal"));
    }
    if (count != static_cast<ssize_t>(sizeof(record))) {
      tail_found = true;
      break;
    }
    if (!record_header_valid(record) || record.sequence != expected ||
        record.checksum != record_checksum(record)) {
      if (offset + static_cast<off_t>(sizeof(record)) < metadata.st_size) {
        throw Error("journal corruption before final record");
      }
      tail_found = true;
      break;
    }
    events_.push_back(decode(record));
    ++expected;
    offset += static_cast<off_t>(sizeof(record));
  }
  if (tail_found) {
  }
  next_sequence_ = expected;
  if (::lseek(fd_.get(), 0, SEEK_END) < 0) {
    throw Error(errno_message("seek journal"));
  }
}

Event Journal::append(std::string type, std::string unit, std::int64_t pid,
                      std::string detail) {
  Event event{next_sequence_, sanitize_token(type), sanitize_token(unit), pid,
              sanitize_token(detail)};
  const DiskRecord record = encode(event);
  const auto* bytes = reinterpret_cast<const std::byte*>(&record);
  write_all(fd_.get(), std::span<const std::byte>(bytes, sizeof(record)));
  if (::fdatasync(fd_.get()) < 0) {
    throw Error(errno_message("sync journal"));
  }
  events_.push_back(event);
  ++next_sequence_;
  return event;
}

const std::vector<Event>& Journal::events() const noexcept { return events_; }

std::string Journal::render() const {
  std::ostringstream output;
  for (const Event& event : events_) {
    output << "EVENT|sequence=" << event.sequence << "|type=" << event.type
           << "|unit=" << event.unit << "|pid=" << event.pid
           << "|detail=" << event.detail << '\n';
  }
  return output.str();
}

}  // namespace guardian
