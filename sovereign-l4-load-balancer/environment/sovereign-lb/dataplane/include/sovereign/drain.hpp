#pragma once
#include "sovereign/connection.hpp"
#include "sovereign/health.hpp"
#include "sovereign/snapshot.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace sovereign {
struct RetiredRuntime {
  std::shared_ptr<const Snapshot> snapshot;
  std::chrono::steady_clock::time_point retired_at;
};

class DrainManager {
 public:
  explicit DrainManager(HealthTracker& health) : health_(health) {}
  void transition(const std::shared_ptr<const Snapshot>& previous,
                  const std::shared_ptr<const Snapshot>& current,
                  std::chrono::steady_clock::time_point now);
  void collect();
  std::size_t retained() const;

 private:
  static std::unordered_map<std::string, const Target*> targets(const Snapshot& snapshot);
  HealthTracker& health_;
  mutable std::mutex mutex_;
  std::vector<RetiredRuntime> retired_;
};
}