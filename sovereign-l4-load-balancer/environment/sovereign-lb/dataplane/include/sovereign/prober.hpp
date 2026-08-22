#pragma once
#include "sovereign/health.hpp"
#include "sovereign/snapshot.hpp"
#include <atomic>
#include <chrono>
#include <mutex>
#include <queue>
#include <string>
#include <unordered_map>

namespace sovereign {
class ActiveProber {
 public:
  ActiveProber(RuntimeStore& runtimes, HealthTracker& tracker)
      : runtimes_(runtimes), tracker_(tracker) {}
  void run(std::atomic_bool& stopping);

 private:
  struct Due {
    std::chrono::steady_clock::time_point at;
    std::string identity;
    std::uint64_t generation{};
    bool operator>(const Due& other) const { return at > other.at; }
  };

  bool probe(const Target& target, const HealthPolicy& policy) const;
  void refresh(const std::shared_ptr<const Snapshot>& snapshot,
               std::chrono::steady_clock::time_point now);
  const std::pair<const Target*, const HealthPolicy*> locate(
      const Snapshot& snapshot, const std::string& identity) const;

  RuntimeStore& runtimes_;
  HealthTracker& tracker_;
  std::uint64_t scheduled_generation_{};
  std::priority_queue<Due, std::vector<Due>, std::greater<Due>> due_;
};
}