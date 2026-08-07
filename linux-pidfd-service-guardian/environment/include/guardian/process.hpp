#pragma once

#include "guardian/common.hpp"
#include "guardian/config.hpp"

#include <chrono>
#include <optional>
#include <string>
#include <sys/types.h>

namespace guardian {

enum class UnitState { stopped, starting, ready, stopping, failed, blocked };

std::string_view state_name(UnitState state);

struct ChildProcess {
  pid_t pid{0};
  pid_t pgid{0};
  UniqueFd pidfd;
  UniqueFd ready_fd;
  UniqueFd stdout_fd;
  UniqueFd stderr_fd;
  UnitState state{UnitState::stopped};
  int restarts{0};
  bool stop_requested{false};
  bool ready_seen{false};
  std::optional<std::chrono::steady_clock::time_point> kill_deadline;

  ChildProcess() = default;
  ChildProcess(const ChildProcess&) = delete;
  ChildProcess& operator=(const ChildProcess&) = delete;
  ChildProcess(ChildProcess&&) noexcept = default;
  ChildProcess& operator=(ChildProcess&&) noexcept = default;
};

struct SpawnResult {
  ChildProcess child;
  std::string error;
};

SpawnResult spawn_process(const UnitConfig& config,
                          const std::filesystem::path& log_path,
                          const std::filesystem::path& state_directory);
void signal_process_group(const ChildProcess& child, int signal_number);
bool process_exists(pid_t pid);
int open_pidfd(pid_t pid);
int send_pidfd_signal(int pidfd, int signal_number);

}  // namespace guardian
