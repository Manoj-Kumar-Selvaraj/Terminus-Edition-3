#pragma once

#include "guardian/common.hpp"

#include <filesystem>
#include <functional>
#include <string>

namespace guardian {

class ControlServer {
 public:
  using Handler = std::function<std::string(const std::string&)>;

  ControlServer(const std::filesystem::path& socket_path, Handler handler);
  ControlServer(const ControlServer&) = delete;
  ControlServer& operator=(const ControlServer&) = delete;
  ~ControlServer();

  [[nodiscard]] int fd() const noexcept;
  void accept_one();

 private:
  std::filesystem::path socket_path_;
  UniqueFd socket_;
  Handler handler_;
};

std::string control_request(const std::filesystem::path& socket_path,
                            const std::string& request);

}  // namespace guardian
