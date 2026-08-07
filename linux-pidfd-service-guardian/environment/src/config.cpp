#include "guardian/config.hpp"

#include "guardian/common.hpp"

#include <algorithm>
#include <charconv>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string_view>

namespace guardian {
namespace {

int parse_integer(std::string_view text, int minimum, int maximum,
                  std::string_view field, std::size_t line_number) {
  int value = 0;
  const auto result =
      std::from_chars(text.data(), text.data() + text.size(), value);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size() ||
      value < minimum || value > maximum) {
    throw Error("invalid " + std::string(field) + " at line " +
                std::to_string(line_number));
  }
  return value;
}

std::pair<std::string, std::string> directive_parts(
    std::string_view line, std::size_t line_number) {
  const std::size_t separator = line.find_first_of(" \t");
  if (separator == std::string_view::npos) {
    return {std::string(line), {}};
  }
  const std::string key(line.substr(0, separator));
  const std::string value = trim(line.substr(separator + 1));
  if (value.empty()) {
    throw Error("missing value at line " + std::to_string(line_number));
  }
  return {key, value};
}

void ensure_singleton(bool& seen, std::string_view field,
                      std::size_t line_number) {
  if (seen) {
    throw Error("duplicate " + std::string(field) + " at line " +
                std::to_string(line_number));
  }
  seen = true;
}

struct Builder {
  UnitConfig config;
  bool executable_seen{false};
  bool restart_seen{false};
  bool restart_limit_seen{false};
  bool grace_seen{false};
};

void validate_finished(const Builder& builder, std::size_t line_number) {
  if (!builder.executable_seen || !builder.restart_seen ||
      !builder.restart_limit_seen || !builder.grace_seen) {
    throw Error("incomplete unit " + builder.config.name + " before line " +
                std::to_string(line_number));
  }
}

std::vector<std::string> sort_graph(const std::map<std::string, UnitConfig>& units) {
  enum class Color { white, gray, black };
  std::map<std::string, Color> colors;
  std::vector<std::string> order;
  for (const auto& [name, ignored] : units) {
    static_cast<void>(ignored);
    colors.emplace(name, Color::white);
  }

  std::function<void(const std::string&)> visit = [&](const std::string& name) {
    const auto color = colors.at(name);
    if (color == Color::gray) {
      throw Error("dependency cycle involving " + name);
    }
    if (color == Color::black) {
      return;
    }
    colors[name] = Color::gray;
    const auto& dependencies = units.at(name).dependencies;
    for (const std::string& dependency : dependencies) {
      if (!units.contains(dependency)) {
        throw Error("unknown dependency " + dependency + " for " + name);
      }
      visit(dependency);
    }
    colors[name] = Color::black;
    order.push_back(name);
  };

  for (const auto& [name, ignored] : units) {
    static_cast<void>(ignored);
    visit(name);
  }
  return order;
}

}  // namespace

Manifest parse_manifest(const std::filesystem::path& path) {
  const std::string content = read_small_file(path, 1024 * 1024);
  std::istringstream input(content);
  std::string raw_line;
  std::optional<Builder> current;
  Manifest manifest;
  std::size_t line_number = 0;

  while (std::getline(input, raw_line)) {
    ++line_number;
    const std::string line = trim(raw_line);
    if (line.empty() || line.front() == '#') {
      continue;
    }
    const auto [key, value] = directive_parts(line, line_number);
    if (key == "unit") {
      if (current.has_value()) {
        throw Error("nested unit at line " + std::to_string(line_number));
      }
      if (!valid_unit_name(value) || manifest.units.contains(value)) {
        throw Error("invalid or duplicate unit at line " +
                    std::to_string(line_number));
      }
      current.emplace();
      current->config.name = value;
      continue;
    }
    if (!current.has_value()) {
      throw Error("directive outside unit at line " +
                  std::to_string(line_number));
    }
    if (key == "end") {
      if (!value.empty()) {
        throw Error("end takes no value at line " +
                    std::to_string(line_number));
      }
      validate_finished(*current, line_number);
      auto config = std::move(current->config);
      manifest.units.emplace(config.name, std::move(config));
      current.reset();
      continue;
    }
    if (key == "exec") {
      ensure_singleton(current->executable_seen, key, line_number);
      std::filesystem::path executable(value);
      if (!executable.is_absolute() || contains_control(value)) {
        throw Error("invalid executable at line " +
                    std::to_string(line_number));
      }
      current->config.executable = std::move(executable);
      continue;
    }
    if (key == "arg") {
      if (contains_control(value) || value.size() > 4096) {
        throw Error("invalid argument at line " +
                    std::to_string(line_number));
      }
      current->config.arguments.push_back(value);
      continue;
    }
    if (key == "depends") {
      if (!valid_unit_name(value) || value == current->config.name) {
        throw Error("invalid dependency at line " +
                    std::to_string(line_number));
      }
      if (std::find(current->config.dependencies.begin(),
                    current->config.dependencies.end(), value) !=
          current->config.dependencies.end()) {
        throw Error("duplicate dependency at line " +
                    std::to_string(line_number));
      }
      current->config.dependencies.push_back(value);
      continue;
    }
    if (key == "restart") {
      ensure_singleton(current->restart_seen, key, line_number);
      if (value == "never") {
        current->config.restart = RestartPolicy::never;
      } else if (value == "on-failure") {
        current->config.restart = RestartPolicy::on_failure;
      } else {
        throw Error("invalid restart policy at line " +
                    std::to_string(line_number));
      }
      continue;
    }
    if (key == "restart-limit") {
      ensure_singleton(current->restart_limit_seen, key, line_number);
      current->config.restart_limit =
          parse_integer(value, 0, 9, key, line_number);
      continue;
    }
    if (key == "stop-grace-ms") {
      ensure_singleton(current->grace_seen, key, line_number);
      current->config.stop_grace_ms =
          parse_integer(value, 50, 5000, key, line_number);
      continue;
    }
    throw Error("unknown directive " + key + " at line " +
                std::to_string(line_number));
  }

  if (current.has_value()) {
    throw Error("unterminated unit " + current->config.name);
  }
  if (manifest.units.empty()) {
    throw Error("manifest contains no units");
  }
  manifest.topological_order = sort_graph(manifest.units);
  manifest.reverse_order = manifest.topological_order;
  std::reverse(manifest.reverse_order.begin(), manifest.reverse_order.end());
  return manifest;
}

std::vector<std::string> dependent_closure(const Manifest& manifest,
                                           const std::string& root) {
  if (!manifest.units.contains(root)) {
    throw Error("unknown unit " + root);
  }
  std::set<std::string> closure{root};
  bool changed = true;
  while (changed) {
    changed = false;
    for (const auto& [name, unit] : manifest.units) {
      if (closure.contains(name)) {
        continue;
      }
      const bool depends = std::any_of(
          unit.dependencies.begin(), unit.dependencies.end(),
          [&](const std::string& dependency) { return closure.contains(dependency); });
      if (depends) {
        closure.insert(name);
        changed = true;
      }
    }
  }
  std::vector<std::string> result;
  for (const std::string& name : manifest.reverse_order) {
    if (closure.contains(name)) {
      result.push_back(name);
    }
  }
  return result;
}

}  // namespace guardian
