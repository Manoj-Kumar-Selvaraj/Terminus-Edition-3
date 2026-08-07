#include "guardian/process.hpp"

#include <array>
#include <cerrno>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace guardian {
namespace {

void close_pipe(std::array<int, 2>& pipe) {
  for (int& fd : pipe) {
    if (fd >= 0) {
      while (::close(fd) < 0 && errno == EINTR) {
      }
      fd = -1;
    }
  }
}

void make_pipe(std::array<int, 2>& pipe, int flags) {
  if (::pipe2(pipe.data(), flags) < 0) {
    throw Error(errno_message("pipe2"));
  }
}

std::vector<char*> argument_vector(const UnitConfig& config,
                                   std::vector<std::string>& storage) {
  storage.clear();
  storage.push_back(config.executable.string());
  storage.insert(storage.end(), config.arguments.begin(), config.arguments.end());
  std::vector<char*> pointers;
  pointers.reserve(storage.size() + 1);
  for (std::string& value : storage) {
    pointers.push_back(value.data());
  }
  pointers.push_back(nullptr);
  return pointers;
}

void child_fail(int error_fd, int code) {
  const int saved = errno;
  static_cast<void>(::write(error_fd, &saved, sizeof(saved)));
  _exit(code);
}

void child_setup_and_exec(const UnitConfig& config,
                          std::array<int, 2>& ready_pipe,
                          std::array<int, 2>& stdout_pipe,
                          std::array<int, 2>& stderr_pipe,
                          std::array<int, 2>& error_pipe,
                          const std::filesystem::path& state_directory) {
  if (::setpgid(0, 0) < 0) {
    child_fail(error_pipe[1], 126);
  }
  if (::dup2(ready_pipe[1], 3) < 0 ||
      ::dup2(stdout_pipe[1], STDOUT_FILENO) < 0 ||
      ::dup2(stderr_pipe[1], STDERR_FILENO) < 0) {
    child_fail(error_pipe[1], 126);
  }
  const int descriptors[] = {ready_pipe[0], ready_pipe[1], stdout_pipe[0],
                             stdout_pipe[1], stderr_pipe[0], stderr_pipe[1],
                             error_pipe[0]};
  for (const int fd : descriptors) {
    if (fd > STDERR_FILENO && fd != 3 && fd != error_pipe[1]) {
      ::close(fd);
    }
  }
  if (::fcntl(3, F_SETFD, 0) < 0) {
    child_fail(error_pipe[1], 126);
  }
  if (::setenv("GUARDIAN_READY_FD", "3", 1) < 0 ||
      ::setenv("GUARDIAN_STATE_DIR", state_directory.c_str(), 1) < 0) {
    child_fail(error_pipe[1], 126);
  }
  std::vector<std::string> storage;
  std::vector<char*> arguments = argument_vector(config, storage);
  ::execv(config.executable.c_str(), arguments.data());
  child_fail(error_pipe[1], 127);
}

std::string read_exec_error(int fd) {
  int child_errno = 0;
  std::byte* destination = reinterpret_cast<std::byte*>(&child_errno);
  std::size_t received = 0;
  while (received < sizeof(child_errno)) {
    const ssize_t count =
        ::read(fd, destination + received, sizeof(child_errno) - received);
    if (count > 0) {
      received += static_cast<std::size_t>(count);
      continue;
    }
    if (count == 0) {
      break;
    }
    if (errno == EINTR) {
      continue;
    }
    return errno_message("exec handshake");
  }
  if (received == 0) {
    return {};
  }
  if (received != sizeof(child_errno)) {
    return "short exec handshake";
  }
  return std::strerror(child_errno);
}

}  // namespace

std::string_view state_name(UnitState state) {
  switch (state) {
    case UnitState::stopped:
      return "stopped";
    case UnitState::starting:
      return "starting";
    case UnitState::ready:
      return "ready";
    case UnitState::stopping:
      return "stopping";
    case UnitState::failed:
      return "failed";
    case UnitState::blocked:
      return "blocked";
  }
  return "unknown";
}

int open_pidfd(pid_t pid) {
#ifdef SYS_pidfd_open
  return static_cast<int>(::syscall(SYS_pidfd_open, pid, 0));
#else
  static_cast<void>(pid);
  errno = ENOSYS;
  return -1;
#endif
}

int send_pidfd_signal(int pidfd, int signal_number) {
#ifdef SYS_pidfd_send_signal
  return static_cast<int>(
      ::syscall(SYS_pidfd_send_signal, pidfd, signal_number, nullptr, 0));
#else
  static_cast<void>(pidfd);
  static_cast<void>(signal_number);
  errno = ENOSYS;
  return -1;
#endif
}

SpawnResult spawn_process(const UnitConfig& config,
                          const std::filesystem::path& log_path,
                          const std::filesystem::path& state_directory) {
  static_cast<void>(log_path);
  std::array<int, 2> ready_pipe{-1, -1};
  std::array<int, 2> stdout_pipe{-1, -1};
  std::array<int, 2> stderr_pipe{-1, -1};
  std::array<int, 2> error_pipe{-1, -1};
  try {
    make_pipe(ready_pipe, O_CLOEXEC | O_NONBLOCK);
    make_pipe(stdout_pipe, O_CLOEXEC | O_NONBLOCK);
    make_pipe(stderr_pipe, O_CLOEXEC | O_NONBLOCK);
    make_pipe(error_pipe, O_CLOEXEC);
  } catch (...) {
    close_pipe(ready_pipe);
    close_pipe(stdout_pipe);
    close_pipe(stderr_pipe);
    close_pipe(error_pipe);
    throw;
  }

  const pid_t pid = ::fork();
  if (pid < 0) {
    close_pipe(ready_pipe);
    close_pipe(stdout_pipe);
    close_pipe(stderr_pipe);
    close_pipe(error_pipe);
    throw Error(errno_message("fork"));
  }
  if (pid == 0) {
    child_setup_and_exec(config, ready_pipe, stdout_pipe, stderr_pipe,
                         error_pipe, state_directory);
  }

  ::close(ready_pipe[1]);
  ready_pipe[1] = -1;
  ::close(stdout_pipe[1]);
  stdout_pipe[1] = -1;
  ::close(stderr_pipe[1]);
  stderr_pipe[1] = -1;
  ::close(error_pipe[1]);
  error_pipe[1] = -1;

  const std::string exec_error = read_exec_error(error_pipe[0]);
  close_pipe(error_pipe);
  if (!exec_error.empty()) {
    int status = 0;
    while (::waitpid(pid, &status, 0) < 0 && errno == EINTR) {
    }
    close_pipe(ready_pipe);
    close_pipe(stdout_pipe);
    close_pipe(stderr_pipe);
    return SpawnResult{ChildProcess{}, exec_error};
  }

  const int pidfd = open_pidfd(pid);
  if (pidfd < 0) {
    ::kill(-pid, SIGKILL);
    int status = 0;
    while (::waitpid(pid, &status, 0) < 0 && errno == EINTR) {
    }
    close_pipe(ready_pipe);
    close_pipe(stdout_pipe);
    close_pipe(stderr_pipe);
    return SpawnResult{ChildProcess{}, errno_message("pidfd_open")};
  }

  ChildProcess child;
  child.pid = pid;
  child.pgid = pid;
  child.pidfd.reset(pidfd);
  child.ready_fd.reset(ready_pipe[0]);
  child.stdout_fd.reset(stdout_pipe[0]);
  child.stderr_fd.reset(stderr_pipe[0]);
  child.state = UnitState::starting;
  return SpawnResult{std::move(child), {}};
}

void signal_process_group(const ChildProcess& child, int signal_number) {
  if (child.pgid <= 0) {
    return;
  }
  if (child.pidfd.valid()) {
    if (send_pidfd_signal(child.pidfd.get(), signal_number) == 0) {
      return;
    }
    if (errno != ENOSYS && errno != EINVAL && errno != ESRCH) {
      throw Error(errno_message("pidfd_send_signal"));
    }
  }
  if (::kill(child.pid, signal_number) < 0 && errno != ESRCH) {
    throw Error(errno_message("kill process"));
  }
}

bool process_exists(pid_t pid) {
  if (pid <= 0) {
    return false;
  }
  if (::kill(pid, 0) == 0) {
    return true;
  }
  return errno == EPERM;
}

}  // namespace guardian
