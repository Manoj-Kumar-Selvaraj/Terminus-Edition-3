#include "sovereign/drain.hpp"

#include <algorithm>

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
}