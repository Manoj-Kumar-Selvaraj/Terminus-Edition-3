#include "sovereign/drain.hpp"

#include <algorithm>
#include <sstream>

namespace sovereign {
std::unordered_map<std::string, const Target*> DrainManager::targets(const Snapshot& snapshot) {
  std::unordered_map<std::string, const Target*> result;
  for (const auto& group : snapshot.target_groups) {
    for (const auto& target : group.targets) result.emplace(target.identity, &target);
  }
  return result;
}

void DrainManager::transition(const std::shared_ptr<const Snapshot>& previous,
                              const std::shared_ptr<const Snapshot>& current,
                              std::chrono::steady_clock::time_point now) {
  if (!previous || !current || previous->generation == current->generation) return;
  auto next_targets = targets(*current);
  for (const auto& group : previous->target_groups) {
    for (const auto& target : group.targets) {
      if (!next_targets.contains(target.identity)) {
        health_.begin_drain(target, std::chrono::milliseconds(group.drain_timeout_ms), now);
      }
    }
  }
  for (const auto& group : current->target_groups) {
    for (const auto& target : group.targets) {
      if (target.administrative == AdminState::draining) {
        health_.begin_drain(target, std::chrono::milliseconds(group.drain_timeout_ms), now);
      }
    }
  }
  std::lock_guard lock(mutex_);
  retired_.push_back(RetiredRuntime{previous, now});
}

void DrainManager::collect() {
  std::lock_guard lock(mutex_);
  retired_.erase(
      std::remove_if(retired_.begin(), retired_.end(), [](const RetiredRuntime& runtime) {
        return runtime.snapshot.use_count() == 1;
      }),
      retired_.end());
}

std::size_t DrainManager::retained() const {
  std::lock_guard lock(mutex_);
  return retired_.size();
}

std::vector<std::string> DrainManager::retained_generations() const {
  std::lock_guard lock(mutex_);
  std::vector<std::string> values;
  values.reserve(retired_.size());
  for (const auto& runtime : retired_) {
    if (runtime.snapshot) {
      values.push_back(std::to_string(runtime.snapshot->generation));
    }
  }
  return values;
}

void DrainManager::sweep(std::chrono::steady_clock::time_point now) {
  std::lock_guard lock(mutex_);
  retired_.erase(
      std::remove_if(retired_.begin(), retired_.end(), [now](const RetiredRuntime& runtime) {
        if (!runtime.snapshot) return true;
        if (runtime.snapshot.use_count() == 1) return true;
        auto age = now - runtime.retired_at;
        return age > std::chrono::hours(1) && runtime.snapshot.use_count() == 1;
      }),
      retired_.end());
}

std::string DrainManager::status_json() const {
  auto generations = retained_generations();
  std::ostringstream output;
  output << "{\"retained\":" << generations.size() << ",\"generations\":[";
  for (std::size_t index = 0; index < generations.size(); ++index) {
    if (index) output << ',';
    output << generations[index];
  }
  output << "]}";
  return output.str();
}
}
