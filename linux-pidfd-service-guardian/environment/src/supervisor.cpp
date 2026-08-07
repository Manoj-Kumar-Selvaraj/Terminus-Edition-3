#include "guardian/supervisor.hpp"

#include "guardian/common.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <linux/limits.h>
#include <sstream>
#include <sys/epoll.h>
#include <sys/file.h>
#include <sys/prctl.h>
#include <sys/signalfd.h>
#include <sys/stat.h>
#include <sys/timerfd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace guardian {
namespace {

constexpr int kMaximumEvents = 64;

std::string exit_detail(int status) {
  if (WIFEXITED(status)) {
    return "exit-" + std::to_string(WEXITSTATUS(status));
  }
  if (WIFSIGNALED(status)) {
    return "signal-" + std::to_string(WTERMSIG(status));
  }
  return "unknown";
}

bool successful_status(int status) {
  return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

bool stopped_state(UnitState state) {
  return state == UnitState::stopped || state == UnitState::failed ||
         state == UnitState::blocked;
}

void arm_periodic_timer(int fd) {
  itimerspec timer{};
  timer.it_value.tv_nsec = 50'000'000;
  timer.it_interval.tv_nsec = 50'000'000;
  if (::timerfd_settime(fd, 0, &timer, nullptr) < 0) {
    throw Error(errno_message("arm timerfd"));
  }
}

}  // namespace

Supervisor::Supervisor(std::filesystem::path manifest_path,
                       std::filesystem::path state_directory)
    : manifest_path_(canonical_parent(manifest_path)),
      state_directory_(canonical_parent(state_directory)),
      socket_path_(state_directory_ / "control.sock"),
      manifest_(parse_manifest(manifest_path_)),
      journal_([&]() {
        std::filesystem::create_directories(state_directory_);
        return state_directory_ / "events.bin";
      }()) {
  for (const auto& [name, config] : manifest_.units) {
    RuntimeUnit runtime;
    runtime.config = config;
    units_.emplace(name, std::move(runtime));
  }
}

void Supervisor::acquire_lock() {
  const auto path = state_directory_ / "guardian.lock";
  lock_fd_.reset(
      ::open(path.c_str(), O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600));
  if (!lock_fd_.valid()) {
    throw Error(errno_message("open guardian lock"));
  }
  if (::flock(lock_fd_.get(), LOCK_EX | LOCK_NB) < 0) {
    if (errno == EWOULDBLOCK) {
      throw Error("guardian already running for state directory");
    }
    throw Error(errno_message("lock state directory"));
  }
  const std::string owner = std::to_string(::getpid()) + "\n";
  if (::ftruncate(lock_fd_.get(), 0) < 0 ||
      ::pwrite(lock_fd_.get(), owner.data(), owner.size(), 0) < 0 ||
      ::fdatasync(lock_fd_.get()) < 0) {
    throw Error(errno_message("write guardian lock"));
  }
}

void Supervisor::initialize_kernel_state() {
  acquire_lock();


  sigset_t mask;
  ::sigemptyset(&mask);
  ::sigaddset(&mask, SIGCHLD);
  ::sigaddset(&mask, SIGTERM);
  ::sigaddset(&mask, SIGINT);
  ::sigaddset(&mask, SIGHUP);
  if (::sigprocmask(SIG_BLOCK, &mask, nullptr) < 0) {
    throw Error(errno_message("block supervisor signals"));
  }
  signal_fd_.reset(::signalfd(-1, &mask, SFD_NONBLOCK | SFD_CLOEXEC));
  if (!signal_fd_.valid()) {
    throw Error(errno_message("create signalfd"));
  }
  timer_fd_.reset(
      ::timerfd_create(CLOCK_MONOTONIC, TFD_NONBLOCK | TFD_CLOEXEC));
  if (!timer_fd_.valid()) {
    throw Error(errno_message("create timerfd"));
  }
  arm_periodic_timer(timer_fd_.get());
  epoll_fd_.reset(::epoll_create1(EPOLL_CLOEXEC));
  if (!epoll_fd_.valid()) {
    throw Error(errno_message("create epoll"));
  }
  control_ = std::make_unique<ControlServer>(
      socket_path_, [this](const std::string& request) {
        return handle_control(request);
      });
  register_fd(signal_fd_.get(), EPOLLIN);
  register_fd(timer_fd_.get(), EPOLLIN);
  register_fd(control_->fd(), EPOLLIN);
}

void Supervisor::register_fd(int fd, std::uint32_t events) {
  epoll_event event{};
  event.events = events;
  event.data.fd = fd;
  if (::epoll_ctl(epoll_fd_.get(), EPOLL_CTL_ADD, fd, &event) < 0) {
    throw Error(errno_message("epoll add"));
  }
}

void Supervisor::unregister_fd(int fd) {
  if (fd < 0 || !epoll_fd_.valid()) {
    return;
  }
  if (::epoll_ctl(epoll_fd_.get(), EPOLL_CTL_DEL, fd, nullptr) < 0 &&
      errno != ENOENT && errno != EBADF) {
    throw Error(errno_message("epoll delete"));
  }
  pidfd_units_.erase(fd);
  stream_units_.erase(fd);
}

bool Supervisor::dependencies_ready(const RuntimeUnit& unit) const {
  return std::all_of(
      unit.config.dependencies.begin(), unit.config.dependencies.end(),
      [&](const std::string& dependency) {
        const auto found = units_.find(dependency);
        if (found == units_.end()) {
          return false;
        }
        const UnitState state = found->second.process.state;
        return state == UnitState::ready || state == UnitState::starting;
      });
}

void Supervisor::start_initial_units() { schedule_ready_units(); }

void Supervisor::schedule_ready_units() {
  bool changed = true;
  while (changed) {
    changed = false;
    for (const std::string& name : manifest_.topological_order) {
      auto found = units_.find(name);
      if (found == units_.end()) {
        continue;
      }
      RuntimeUnit& unit = found->second;
      if (!unit.desired || unit.process.state != UnitState::stopped ||
          !dependencies_ready(unit)) {
        continue;
      }
      if (start_unit(name, false)) {
        changed = true;
      }
    }
  }
}

bool Supervisor::start_unit(const std::string& name, bool is_restart) {
  RuntimeUnit& unit = units_.at(name);
  if (!unit.desired || !dependencies_ready(unit) ||
      !stopped_state(unit.process.state)) {
    return false;
  }
  const int restart_count = unit.process.restarts;
  SpawnResult result = spawn_process(
      unit.config, state_directory_ / (name + ".log"), state_directory_);
  if (!result.error.empty()) {
    unit.process.state = UnitState::failed;
    journal_.append("unit-failed", name, 0, "exec");
    block_dependents(name);
    return false;
  }
  unit.process = std::move(result.child);
  unit.process.restarts = restart_count;
  pidfd_units_[unit.process.pidfd.get()] = name;
  stream_units_[unit.process.ready_fd.get()] = {name, "ready"};
  stream_units_[unit.process.stdout_fd.get()] = {name, "stdout"};
  stream_units_[unit.process.stderr_fd.get()] = {name, "stderr"};
  register_fd(unit.process.pidfd.get(), EPOLLIN | EPOLLHUP);
  register_fd(unit.process.ready_fd.get(), EPOLLIN | EPOLLHUP);
  register_fd(unit.process.stdout_fd.get(), EPOLLIN | EPOLLHUP);
  register_fd(unit.process.stderr_fd.get(), EPOLLIN | EPOLLHUP);
  journal_.append("unit-starting", name, unit.process.pid,
                  is_restart ? "restart" : "start");
  return true;
}

void Supervisor::request_stop(const std::string& name, std::string detail) {
  auto found = units_.find(name);
  if (found == units_.end()) {
    return;
  }
  RuntimeUnit& unit = found->second;
  if (stopped_state(unit.process.state)) {
    return;
  }
  if (unit.process.state == UnitState::stopping) {
    return;
  }
  unit.process.stop_requested = true;
  unit.process.state = UnitState::stopping;
  unit.process.kill_deadline = std::chrono::steady_clock::now() +
                               std::chrono::milliseconds(
                                   unit.config.stop_grace_ms);
  journal_.append("unit-stopping", name, unit.process.pid, std::move(detail));
  signal_process_group(unit.process, SIGTERM);
}

void Supervisor::stop_dependent_closure(const std::string& name) {
  for (const std::string& item : dependent_closure(manifest_, name)) {
    request_stop(item, item == name ? "requested" : "dependency");
  }
}

void Supervisor::force_expired_stops() {
  const auto now = std::chrono::steady_clock::now();
  for (auto& [name, unit] : units_) {
    static_cast<void>(name);
    if (unit.process.state != UnitState::stopping ||
        !unit.process.kill_deadline.has_value() ||
        now < *unit.process.kill_deadline) {
      continue;
    }
    signal_process_group(unit.process, SIGKILL);
    unit.process.kill_deadline.reset();
  }
}

void Supervisor::handle_signal_events() {
  while (true) {
    signalfd_siginfo information{};
    const ssize_t count =
        ::read(signal_fd_.get(), &information, sizeof(information));
    if (count < 0 && errno == EINTR) {
      continue;
    }
    if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
      return;
    }
    if (count != static_cast<ssize_t>(sizeof(information))) {
      return;
    }
    if (information.ssi_signo == SIGCHLD) {
      reap_children();
    } else if (information.ssi_signo == SIGHUP) {
      static_cast<void>(reload_manifest());
    } else if (information.ssi_signo == SIGTERM ||
               information.ssi_signo == SIGINT) {
      begin_shutdown();
    }
  }
}

void Supervisor::reap_children() {
  while (true) {
    int status = 0;
    const pid_t pid = ::waitpid(-1, &status, WNOHANG);
    if (pid == 0) {
      return;
    }
    if (pid < 0) {
      if (errno == EINTR) {
        continue;
      }
      if (errno == ECHILD) {
        return;
      }
      throw Error(errno_message("waitpid"));
    }
    auto unit = std::find_if(units_.begin(), units_.end(), [&](const auto& item) {
      return item.second.process.pid == pid;
    });
    if (unit != units_.end()) {
      handle_child_exit(unit->first, status);
    } else {
      handle_adopted_exit(pid, status);
    }
  }
}

void Supervisor::handle_pidfd(int fd) {
  const auto found = pidfd_units_.find(fd);
  if (found == pidfd_units_.end()) {
    return;
  }
  const std::string name = found->second;
  const pid_t pid = units_.at(name).process.pid;
  int status = 0;
  const pid_t result = ::waitpid(pid, &status, WNOHANG);
  if (result == pid) {
    handle_child_exit(name, status);
  }
}

void Supervisor::handle_ready_fd(int fd) {
  const auto mapping = stream_units_.find(fd);
  if (mapping == stream_units_.end()) {
    return;
  }
  const std::string name = mapping->second.first;
  RuntimeUnit& unit = units_.at(name);
  std::array<char, 64> buffer{};
  const ssize_t count = ::read(fd, buffer.data(), buffer.size());
  if (count > 0 && !unit.process.ready_seen) {
    unit.process.ready_seen = true;
    unit.process.state = UnitState::ready;
    journal_.append("unit-ready", name, unit.process.pid, "ready");
    schedule_ready_units();
  }
  if (count == 0 || (count < 0 && errno != EAGAIN && errno != EWOULDBLOCK &&
                     errno != EINTR)) {
    unregister_fd(fd);
    unit.process.ready_fd.reset();
    if (!unit.process.ready_seen && unit.process.state == UnitState::starting) {
      unit.process.stop_requested = false;
      signal_process_group(unit.process, SIGKILL);
    }
  }
}

void Supervisor::append_log(const std::string& name, const std::string& stream,
                            std::string_view data) {
  const auto path = state_directory_ / (name + ".log");
  UniqueFd fd(::open(path.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC |
                                       O_NOFOLLOW,
                     0600));
  if (!fd.valid()) {
    throw Error(errno_message("open unit log"));
  }
  write_all(fd.get(), stream + "|");
  write_all(fd.get(), data);
  if (data.empty() || data.back() != '\n') {
    write_all(fd.get(), "\n");
  }
}

void Supervisor::handle_stream_fd(int fd) {
  const auto mapping = stream_units_.find(fd);
  if (mapping == stream_units_.end()) {
    return;
  }
  const std::string name = mapping->second.first;
  const std::string stream = mapping->second.second;
  std::array<char, 4096> buffer{};
  while (true) {
    const ssize_t count = ::read(fd, buffer.data(), buffer.size());
    if (count > 0) {
      append_log(name, stream,
                 std::string_view(buffer.data(), static_cast<std::size_t>(count)));
      continue;
    }
    if (count < 0 && errno == EINTR) {
      continue;
    }
    if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
      return;
    }
    unregister_fd(fd);
    RuntimeUnit& unit = units_.at(name);
    if (stream == "stdout") {
      unit.process.stdout_fd.reset();
    } else {
      unit.process.stderr_fd.reset();
    }
    return;
  }
}

void Supervisor::finish_stopped(RuntimeUnit& unit, std::string detail) {
  const std::string name = unit.config.name;
  const pid_t old_pid = unit.process.pid;
  const int restarts = unit.process.restarts;
  const bool replacement = unit.replacement_pending;
  const bool desired = unit.desired;
  unit.process = ChildProcess{};
  unit.process.restarts = restarts;
  unit.process.state = UnitState::stopped;
  journal_.append("unit-stopped", name, old_pid, std::move(detail));
  if (replacement && desired) {
    unit.replacement_pending = false;
    start_unit(name, false);
  }
}

void Supervisor::handle_child_exit(const std::string& name, int status) {
  RuntimeUnit& unit = units_.at(name);
  const pid_t old_pid = unit.process.pid;
  unregister_fd(unit.process.pidfd.get());
  unregister_fd(unit.process.ready_fd.get());
  unregister_fd(unit.process.stdout_fd.get());
  unregister_fd(unit.process.stderr_fd.get());
  journal_.append("unit-exit", name, old_pid, exit_detail(status));

  if (unit.process.stop_requested || shutting_down_ || !unit.desired ||
      successful_status(status)) {
    finish_stopped(unit, unit.process.stop_requested ? "stopped" : "exited");
    return;
  }

  const int previous_restarts = unit.process.restarts;
  unit.process = ChildProcess{};
  unit.process.restarts = previous_restarts;
  if (unit.config.restart == RestartPolicy::on_failure &&
      previous_restarts < unit.config.restart_limit) {
    ++unit.process.restarts;
    journal_.append("unit-restart", name, old_pid,
                    std::to_string(unit.process.restarts));
    start_unit(name, true);
    return;
  }
  unit.process.state = UnitState::failed;
  journal_.append("unit-failed", name, old_pid, "budget");
  block_dependents(name);
}

void Supervisor::handle_adopted_exit(pid_t pid, int status) {
  adopted_children_.erase(pid);
  journal_.append("unit-exit", "guardian", pid, exit_detail(status));
}

void Supervisor::block_dependents(const std::string& name) {
  const auto closure = dependent_closure(manifest_, name);
  for (const std::string& dependent : closure) {
    if (dependent == name) {
      continue;
    }
    RuntimeUnit& unit = units_.at(dependent);
    unit.desired = false;
    if (!stopped_state(unit.process.state)) {
      request_stop(dependent, "blocked");
    }
    unit.process.state = UnitState::blocked;
    journal_.append("unit-blocked", dependent, unit.process.pid, name);
  }
}

std::string Supervisor::status_response() const {
  std::ostringstream output;
  for (const auto& [name, unit] : units_) {
    output << "UNIT|name=" << name << "|state="
           << state_name(unit.process.state) << "|pid=" << unit.process.pid
           << "|restarts=" << unit.process.restarts << '\n';
  }
  return output.str();
}

std::string Supervisor::reload_manifest() {
  Manifest replacement;
  try {
    replacement = parse_manifest(manifest_path_);
  } catch (const std::exception&) {
    journal_.append("reload-rejected", "guardian", 0, "manifest");
    return "ERR|code=INVALID_MANIFEST\n";
  }

  for (auto& [name, unit] : units_) {
    const auto next = replacement.units.find(name);
    if (next == replacement.units.end()) {
      unit.desired = false;
      stop_dependent_closure(name);
    } else if (!(next->second == unit.config)) {
      unit.config = next->second;
      unit.replacement_pending = true;
      stop_dependent_closure(name);
    }
  }
  for (const auto& [name, config] : replacement.units) {
    if (!units_.contains(name)) {
      RuntimeUnit runtime;
      runtime.config = config;
      units_.emplace(name, std::move(runtime));
    }
  }
  manifest_ = std::move(replacement);
  for (auto& [name, unit] : units_) {
    static_cast<void>(name);
    unit.process.restarts = 0;
  }
  journal_.append("reload-accepted", "guardian", 0, "manifest");
  schedule_ready_units();
  return "OK|command=RELOAD\n";
}

std::string Supervisor::handle_control(const std::string& request) {
  const std::vector<std::string> words = split_words(request);
  if (words.empty()) {
    return "ERR|code=EMPTY_REQUEST\n";
  }
  if (words[0] == "STATUS" && words.size() == 1) {
    return status_response();
  }
  if (words[0] == "EVENTS" && words.size() == 1) {
    return journal_.render();
  }
  if (words[0] == "RELOAD" && words.size() == 1) {
    return reload_manifest();
  }
  if (words[0] == "SHUTDOWN" && words.size() == 1) {
    begin_shutdown();
    return "OK|command=SHUTDOWN\n";
  }
  if ((words[0] == "START" || words[0] == "STOP") && words.size() == 2) {
    const auto found = units_.find(words[1]);
    if (found == units_.end()) {
      return "ERR|code=UNKNOWN_UNIT\n";
    }
    if (words[0] == "START") {
      RuntimeUnit& unit = found->second;
      unit.desired = true;
      if (unit.process.state == UnitState::blocked ||
          unit.process.state == UnitState::failed) {
        unit.process.state = UnitState::stopped;
      }
      schedule_ready_units();
      return "OK|command=START\n";
    }
    found->second.desired = false;
    stop_dependent_closure(words[1]);
    return "OK|command=STOP\n";
  }
  return "ERR|code=BAD_REQUEST\n";
}

void Supervisor::begin_shutdown() {
  if (shutting_down_) {
    return;
  }
  shutting_down_ = true;
  for (const std::string& name : manifest_.reverse_order) {
    auto found = units_.find(name);
    if (found == units_.end()) {
      continue;
    }
    found->second.desired = false;
    request_stop(name, "shutdown");
  }
}

bool Supervisor::shutdown_complete() const {
  const bool units_stopped = std::all_of(
      units_.begin(), units_.end(), [](const auto& entry) {
        return stopped_state(entry.second.process.state);
      });
  if (!units_stopped) {
    return false;
  }
  siginfo_t information{};
  const int result =
      ::waitid(P_ALL, 0, &information, WEXITED | WNOHANG | WNOWAIT);
  return result < 0 && errno == ECHILD;
}

int Supervisor::run() {
  initialize_kernel_state();
  journal_.append("guardian-start", "guardian", ::getpid(), "run");
  start_initial_units();
  std::array<epoll_event, kMaximumEvents> events{};

  while (!exit_requested_) {
    const int count = ::epoll_wait(epoll_fd_.get(), events.data(),
                                   static_cast<int>(events.size()), -1);
    if (count < 0) {
      if (errno == EINTR) {
        continue;
      }
      throw Error(errno_message("epoll_wait"));
    }
    for (int index = 0; index < count; ++index) {
      const int fd = events[static_cast<std::size_t>(index)].data.fd;
      if (fd == signal_fd_.get()) {
        handle_signal_events();
      } else if (fd == timer_fd_.get()) {
        std::uint64_t expirations = 0;
        static_cast<void>(::read(fd, &expirations, sizeof(expirations)));
        force_expired_stops();
        reap_children();
      } else if (control_ && fd == control_->fd()) {
        control_->accept_one();
      } else if (pidfd_units_.contains(fd)) {
        handle_pidfd(fd);
      } else if (stream_units_.contains(fd) &&
                 stream_units_.at(fd).second == "ready") {
        handle_ready_fd(fd);
      } else if (stream_units_.contains(fd)) {
        handle_stream_fd(fd);
      }
    }
    if (shutting_down_ && shutdown_complete()) {
      exit_requested_ = true;
    }
  }
  journal_.append("guardian-stop", "guardian", ::getpid(), "clean");
  return 0;
}

}  // namespace guardian
