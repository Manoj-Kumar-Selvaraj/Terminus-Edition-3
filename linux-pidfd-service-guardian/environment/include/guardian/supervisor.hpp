#pragma once

#include "guardian/config.hpp"
#include "guardian/control.hpp"
#include "guardian/journal.hpp"
#include "guardian/process.hpp"

#include <filesystem>
#include <map>
#include <memory>
#include <set>
#include <string>

namespace guardian {

struct RuntimeUnit {
  UnitConfig config;
  ChildProcess process;
  bool desired{true};
  bool replacement_pending{false};
};

class Supervisor {
 public:
  Supervisor(std::filesystem::path manifest_path,
             std::filesystem::path state_directory);
  int run();

 private:
  std::filesystem::path manifest_path_;
  std::filesystem::path state_directory_;
  std::filesystem::path socket_path_;
  Manifest manifest_;
  Journal journal_;
  UniqueFd lock_fd_;
  UniqueFd epoll_fd_;
  UniqueFd signal_fd_;
  UniqueFd timer_fd_;
  std::unique_ptr<ControlServer> control_;
  std::map<std::string, RuntimeUnit> units_;
  std::map<int, std::string> pidfd_units_;
  std::map<int, std::pair<std::string, std::string>> stream_units_;
  std::set<pid_t> adopted_children_;
  bool shutting_down_{false};
  bool exit_requested_{false};

  void initialize_kernel_state();
  void acquire_lock();
  void register_fd(int fd, std::uint32_t events);
  void unregister_fd(int fd);
  void start_initial_units();
  bool dependencies_ready(const RuntimeUnit& unit) const;
  void schedule_ready_units();
  bool start_unit(const std::string& name, bool is_restart);
  void request_stop(const std::string& name, std::string detail);
  void stop_dependent_closure(const std::string& name);
  void force_expired_stops();
  void handle_signal_events();
  void reap_children();
  void handle_pidfd(int fd);
  void handle_ready_fd(int fd);
  void handle_stream_fd(int fd);
  void handle_child_exit(const std::string& name, int status);
  void handle_adopted_exit(pid_t pid, int status);
  void finish_stopped(RuntimeUnit& unit, std::string detail);
  void block_dependents(const std::string& name);
  void append_log(const std::string& name, const std::string& stream,
                  std::string_view data);
  std::string handle_control(const std::string& request);
  std::string status_response() const;
  std::string reload_manifest();
  void begin_shutdown();
  bool shutdown_complete() const;
};

}  // namespace guardian
