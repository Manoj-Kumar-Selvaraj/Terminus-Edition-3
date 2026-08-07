#pragma once

#include <filesystem>
#include <map>
#include <string>
#include <vector>

namespace guardian {

enum class RestartPolicy { never, on_failure };

struct UnitConfig {
  std::string name;
  std::filesystem::path executable;
  std::vector<std::string> arguments;
  std::vector<std::string> dependencies;
  RestartPolicy restart{RestartPolicy::never};
  int restart_limit{-1};
  int stop_grace_ms{-1};

  [[nodiscard]] bool operator==(const UnitConfig& other) const = default;
};

struct Manifest {
  std::map<std::string, UnitConfig> units;
  std::vector<std::string> topological_order;
  std::vector<std::string> reverse_order;
};

Manifest parse_manifest(const std::filesystem::path& path);
std::vector<std::string> dependent_closure(const Manifest& manifest,
                                           const std::string& root);

}  // namespace guardian
