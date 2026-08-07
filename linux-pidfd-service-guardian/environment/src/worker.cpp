#include <array>
#include <cerrno>
#include <charconv>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

namespace {

volatile sig_atomic_t stop_requested = 0;

void handle_term(int) { stop_requested = 1; }

struct Options {
  std::string name{"worker"};
  std::filesystem::path ready_file;
  std::filesystem::path term_file;
  std::filesystem::path child_file;
  std::filesystem::path crash_file;
  std::filesystem::path ready_gate_file;
  int exit_code{-1};
};

int parse_int(std::string_view value) {
  int result = 0;
  const auto parsed =
      std::from_chars(value.data(), value.data() + value.size(), result);
  if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size()) {
    throw std::runtime_error("invalid integer");
  }
  return result;
}

Options parse_options(int argc, char** argv) {
  Options options;
  for (int index = 1; index < argc; ++index) {
    const std::string_view key(argv[index]);
    if (index + 1 >= argc) {
      throw std::runtime_error("missing option value");
    }
    const std::string value(argv[++index]);
    if (key == "--name") {
      options.name = value;
    } else if (key == "--ready-file") {
      options.ready_file = value;
    } else if (key == "--term-file") {
      options.term_file = value;
    } else if (key == "--spawn-child-file") {
      options.child_file = value;
    } else if (key == "--exit-code") {
      options.exit_code = parse_int(value);
    } else if (key == "--crash-count-file") {
      options.crash_file = value;
    } else if (key == "--ready-gate-file") {
      options.ready_gate_file = value;
    } else {
      throw std::runtime_error("unknown option");
    }
  }
  return options;
}

void wait_for_gate(const std::filesystem::path& path) {
  if (path.empty()) {
    return;
  }
  const timespec pause{0, 10'000'000};
  while (!stop_requested && !std::filesystem::exists(path)) {
    timespec remaining{};
    if (::nanosleep(&pause, &remaining) < 0 && errno != EINTR) {
      throw std::runtime_error("ready gate wait failed");
    }
  }
}

void write_text(const std::filesystem::path& path, std::string_view text) {
  if (path.empty()) {
    return;
  }
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  if (!output) {
    throw std::runtime_error("cannot write fixture file");
  }
  output << text;
  output.flush();
  if (!output) {
    throw std::runtime_error("cannot flush fixture file");
  }
}

bool consume_crash(const std::filesystem::path& path) {
  if (path.empty()) {
    return false;
  }
  int remaining = 0;
  {
    std::ifstream input(path);
    if (input) {
      input >> remaining;
    }
  }
  if (remaining <= 0) {
    return false;
  }
  write_text(path, std::to_string(remaining - 1) + "\n");
  return true;
}

int readiness_fd() {
  const char* value = std::getenv("GUARDIAN_READY_FD");
  if (value == nullptr) {
    throw std::runtime_error("GUARDIAN_READY_FD is missing");
  }
  return parse_int(value);
}

pid_t spawn_descendant(const std::filesystem::path& child_file) {
  if (child_file.empty()) {
    return 0;
  }
  const pid_t child = ::fork();
  if (child < 0) {
    throw std::runtime_error("fork descendant failed");
  }
  if (child == 0) {
    ::signal(SIGTERM, SIG_IGN);
    ::signal(SIGINT, SIG_IGN);
    while (true) {
      ::pause();
    }
  }
  write_text(child_file, std::to_string(child) + "\n");
  return child;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options options = parse_options(argc, argv);
    if (consume_crash(options.crash_file)) {
      std::cerr << options.name << " crashes before readiness\n";
      return options.exit_code >= 0 ? options.exit_code : 23;
    }
    if (options.exit_code >= 0 && options.crash_file.empty()) {
      return options.exit_code;
    }
    struct sigaction action {};
    action.sa_handler = handle_term;
    ::sigemptyset(&action.sa_mask);
    if (::sigaction(SIGTERM, &action, nullptr) < 0 ||
        ::sigaction(SIGINT, &action, nullptr) < 0) {
      throw std::runtime_error("sigaction failed");
    }
    const pid_t descendant = spawn_descendant(options.child_file);
    wait_for_gate(options.ready_gate_file);
    if (stop_requested) {
      return 0;
    }
    write_text(options.ready_file, std::to_string(::getpid()) + "\n");
    const int ready = readiness_fd();
    const char marker = 'R';
    if (::write(ready, &marker, 1) != 1) {
      throw std::runtime_error("readiness write failed");
    }
    ::close(ready);
    std::cout << options.name << " ready pid=" << ::getpid() << '\n';
    std::cout.flush();
    while (!stop_requested) {
      ::pause();
    }
    write_text(options.term_file, std::to_string(::getpid()) + "\n");
    if (descendant > 0) {
      int status = 0;
      while (::waitpid(descendant, &status, 0) < 0 && errno == EINTR) {
      }
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "guardian-worker: " << error.what() << '\n';
    return 2;
  }
}
