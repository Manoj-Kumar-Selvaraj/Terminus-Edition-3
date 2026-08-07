#pragma once

#include "guardian/common.hpp"

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace guardian {

struct Event {
  std::uint64_t sequence{0};
  std::string type;
  std::string unit;
  std::int64_t pid{0};
  std::string detail;
};

class Journal {
 public:
  explicit Journal(const std::filesystem::path& path);
  Journal(const Journal&) = delete;
  Journal& operator=(const Journal&) = delete;

  Event append(std::string type, std::string unit, std::int64_t pid,
               std::string detail);
  [[nodiscard]] const std::vector<Event>& events() const noexcept;
  [[nodiscard]] std::string render() const;

 private:
  UniqueFd fd_;
  std::filesystem::path path_;
  std::vector<Event> events_;
  std::uint64_t next_sequence_{1};

  void recover();
};

}  // namespace guardian
