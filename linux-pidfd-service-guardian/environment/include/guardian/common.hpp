#pragma once

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace guardian {

class Error : public std::runtime_error {
 public:
  explicit Error(const std::string& message);
};

class UniqueFd {
 public:
  UniqueFd() noexcept = default;
  explicit UniqueFd(int fd) noexcept;
  ~UniqueFd();
  UniqueFd(const UniqueFd&) = delete;
  UniqueFd& operator=(const UniqueFd&) = delete;
  UniqueFd(UniqueFd&& other) noexcept;
  UniqueFd& operator=(UniqueFd&& other) noexcept;
  [[nodiscard]] int get() const noexcept;
  [[nodiscard]] bool valid() const noexcept;
  int release() noexcept;
  void reset(int fd = -1) noexcept;

 private:
  int fd_{-1};
};

std::string errno_message(std::string_view action);
void set_nonblocking(int fd);
void set_close_on_exec(int fd);
void write_all(int fd, std::span<const std::byte> bytes);
void write_all(int fd, std::string_view text);
std::string trim(std::string_view value);
std::vector<std::string> split_words(std::string_view value);
bool valid_unit_name(std::string_view name);
bool contains_control(std::string_view value);
std::uint32_t crc32(std::span<const std::byte> bytes);
std::filesystem::path canonical_parent(const std::filesystem::path& path);
std::string read_small_file(const std::filesystem::path& path,
                            std::size_t limit);
void atomic_write(const std::filesystem::path& path, std::string_view text,
                  unsigned mode);
std::uint64_t monotonic_millis();
std::string join(const std::vector<std::string>& values,
                 std::string_view separator);
std::string sanitize_token(std::string_view value);

}  // namespace guardian
