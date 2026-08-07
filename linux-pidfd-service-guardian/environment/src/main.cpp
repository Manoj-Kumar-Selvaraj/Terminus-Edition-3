#include "guardian/common.hpp"
#include "guardian/supervisor.hpp"

#include <exception>
#include <filesystem>
#include <iostream>
#include <string_view>

namespace {

int usage() {
  std::cerr << "usage: guardian run <manifest> <state-directory>\n";
  return 2;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 4 || std::string_view(argv[1]) != "run") {
    return usage();
  }
  try {
    guardian::Supervisor supervisor{std::filesystem::path(argv[2]),
                                    std::filesystem::path(argv[3])};
    return supervisor.run();
  } catch (const std::exception& error) {
    std::cerr << "guardian: " << error.what() << '\n';
    return 1;
  }
}
