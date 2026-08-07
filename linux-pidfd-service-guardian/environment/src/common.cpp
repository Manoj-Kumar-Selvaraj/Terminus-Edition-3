#include "guardian/common.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <charconv>
#include <cctype>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <limits>
#include <sstream>
#include <system_error>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

namespace guardian {

Error::Error(const std::string& message) : std::runtime_error(message) {}

UniqueFd::UniqueFd(int fd) noexcept : fd_(fd) {}

UniqueFd::~UniqueFd() {
  if (fd_ >= 0) {
    while (::close(fd_) < 0 && errno == EINTR) {
    }
  }
}

UniqueFd::UniqueFd(UniqueFd&& other) noexcept : fd_(other.release()) {}

UniqueFd& UniqueFd::operator=(UniqueFd&& other) noexcept {
  if (this != &other) {
    reset(other.release());
  }
  return *this;
}

int UniqueFd::get() const noexcept { return fd_; }

bool UniqueFd::valid() const noexcept { return fd_ >= 0; }

int UniqueFd::release() noexcept {
  const int result = fd_;
  fd_ = -1;
  return result;
}

void UniqueFd::reset(int fd) noexcept {
  if (fd_ >= 0) {
    while (::close(fd_) < 0 && errno == EINTR) {
    }
  }
  fd_ = fd;
}

std::string errno_message(std::string_view action) {
  std::string result(action);
  result.append(": ");
  result.append(std::strerror(errno));
  return result;
}

void set_nonblocking(int fd) {
  const int flags = ::fcntl(fd, F_GETFL);
  if (flags < 0 || ::fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
    throw Error(errno_message("fcntl nonblocking"));
  }
}

void set_close_on_exec(int fd) {
  const int flags = ::fcntl(fd, F_GETFD);
  if (flags < 0 || ::fcntl(fd, F_SETFD, flags | FD_CLOEXEC) < 0) {
    throw Error(errno_message("fcntl close-on-exec"));
  }
}

void write_all(int fd, std::span<const std::byte> bytes) {
  std::size_t offset = 0;
  while (offset < bytes.size()) {
    const auto* data = bytes.data() + offset;
    const std::size_t remaining = bytes.size() - offset;
    const ssize_t count = ::write(fd, data, remaining);
    if (count > 0) {
      offset += static_cast<std::size_t>(count);
      continue;
    }
    if (count < 0 && errno == EINTR) {
      continue;
    }
    throw Error(errno_message("write"));
  }
}

void write_all(int fd, std::string_view text) {
  const auto* data = reinterpret_cast<const std::byte*>(text.data());
  write_all(fd, std::span<const std::byte>(data, text.size()));
}

std::string trim(std::string_view value) {
  std::size_t first = 0;
  while (first < value.size() &&
         std::isspace(static_cast<unsigned char>(value[first]))) {
    ++first;
  }
  std::size_t last = value.size();
  while (last > first &&
         std::isspace(static_cast<unsigned char>(value[last - 1]))) {
    --last;
  }
  return std::string(value.substr(first, last - first));
}

std::vector<std::string> split_words(std::string_view value) {
  std::vector<std::string> result;
  std::size_t cursor = 0;
  while (cursor < value.size()) {
    while (cursor < value.size() &&
           std::isspace(static_cast<unsigned char>(value[cursor]))) {
      ++cursor;
    }
    if (cursor >= value.size()) {
      break;
    }
    const std::size_t start = cursor;
    while (cursor < value.size() &&
           !std::isspace(static_cast<unsigned char>(value[cursor]))) {
      ++cursor;
    }
    result.emplace_back(value.substr(start, cursor - start));
  }
  return result;
}

bool valid_unit_name(std::string_view name) {
  if (name.empty() || name.size() > 48) {
    return false;
  }
  if (name.front() == '-' || name.back() == '-') {
    return false;
  }
  for (const char value : name) {
    const auto byte = static_cast<unsigned char>(value);
    if (!(std::islower(byte) || std::isdigit(byte) || value == '-')) {
      return false;
    }
  }
  return true;
}

bool contains_control(std::string_view value) {
  return std::any_of(value.begin(), value.end(), [](char item) {
    const auto byte = static_cast<unsigned char>(item);
    return byte < 0x20 || byte == 0x7f;
  });
}

std::uint32_t crc32(std::span<const std::byte> bytes) {
  std::uint32_t crc = 0xffffffffU;
  for (const std::byte value : bytes) {
    crc ^= static_cast<std::uint32_t>(std::to_integer<unsigned char>(value));
    for (int bit = 0; bit < 8; ++bit) {
      const std::uint32_t mask = 0U - (crc & 1U);
      crc = (crc >> 1U) ^ (0xedb88320U & mask);
    }
  }
  return ~crc;
}

std::filesystem::path canonical_parent(const std::filesystem::path& path) {
  const auto parent = path.parent_path();
  std::error_code error;
  auto canonical = std::filesystem::weakly_canonical(parent, error);
  if (error) {
    throw Error("cannot resolve parent: " + error.message());
  }
  return canonical / path.filename();
}

std::string read_small_file(const std::filesystem::path& path,
                            std::size_t limit) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    throw Error("cannot open " + path.string());
  }
  std::string result;
  std::array<char, 4096> buffer{};
  while (stream) {
    stream.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    const auto count = static_cast<std::size_t>(stream.gcount());
    if (result.size() + count > limit) {
      throw Error("file exceeds size limit: " + path.string());
    }
    result.append(buffer.data(), count);
  }
  return result;
}

void atomic_write(const std::filesystem::path& path, std::string_view text,
                  unsigned mode) {
  const auto temporary = path.string() + ".new";
  UniqueFd fd(::open(temporary.c_str(),
                     O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
                     static_cast<mode_t>(mode)));
  if (!fd.valid()) {
    throw Error(errno_message("open temporary"));
  }
  write_all(fd.get(), text);
  if (::fdatasync(fd.get()) < 0) {
    throw Error(errno_message("fdatasync temporary"));
  }
  fd.reset();
  if (::rename(temporary.c_str(), path.c_str()) < 0) {
    throw Error(errno_message("rename temporary"));
  }
  UniqueFd parent(::open(path.parent_path().c_str(), O_RDONLY | O_DIRECTORY));
  if (!parent.valid() || ::fsync(parent.get()) < 0) {
    throw Error(errno_message("fsync parent"));
  }
}

std::uint64_t monotonic_millis() {
  timespec now{};
  if (::clock_gettime(CLOCK_MONOTONIC, &now) < 0) {
    throw Error(errno_message("clock_gettime"));
  }
  return static_cast<std::uint64_t>(now.tv_sec) * 1000ULL +
         static_cast<std::uint64_t>(now.tv_nsec / 1000000L);
}

std::string join(const std::vector<std::string>& values,
                 std::string_view separator) {
  std::string result;
  for (std::size_t index = 0; index < values.size(); ++index) {
    if (index != 0) {
      result.append(separator);
    }
    result.append(values[index]);
  }
  return result;
}

std::string sanitize_token(std::string_view value) {
  std::string result;
  result.reserve(value.size());
  for (const char character : value) {
    const auto byte = static_cast<unsigned char>(character);
    if (std::isalnum(byte) || character == '-' || character == '_' ||
        character == '.' || character == ':' || character == '/') {
      result.push_back(character);
    } else {
      result.push_back('_');
    }
  }
  return result.empty() ? "none" : result;
}

}  // namespace guardian
