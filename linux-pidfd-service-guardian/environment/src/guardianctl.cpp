#include "guardian/common.hpp"
#include "guardian/control.hpp"

#include <exception>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
  if (argc < 3) {
    std::cerr << "usage: guardianctl <socket> <command> [argument]\n";
    return 2;
  }
  try {
    std::vector<std::string> words;
    for (int index = 2; index < argc; ++index) {
      words.emplace_back(argv[index]);
    }
    const std::string request = guardian::join(words, " ");
    std::cout << guardian::control_request(std::filesystem::path(argv[1]),
                                           request);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "guardianctl: " << error.what() << '\n';
    return 1;
  }
}
