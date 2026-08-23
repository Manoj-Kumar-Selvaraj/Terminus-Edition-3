#pragma once
#include "sovereign/snapshot.hpp"
#include <chrono>
#include <unordered_map>

namespace sovereign {
struct TargetRuntime { bool active_healthy{true}; std::chrono::steady_clock::time_point ejected_until{}; std::chrono::steady_clock::time_point drain_deadline{}; std::uint64_t active_connections{}; };
class Eligibility {
 public:
  TargetRuntime& state(const std::string& identity) { return states_[identity]; }
  const TargetRuntime& state(const std::string& identity) const;
  std::vector<const Target*> eligible(const TargetGroup& group,const std::string& local_zone,std::chrono::steady_clock::time_point now) const;
 private:
  bool normally_eligible(const Target& target,std::chrono::steady_clock::time_point now) const;
  bool fail_open_eligible(const Target& target,std::chrono::steady_clock::time_point now) const;
  std::unordered_map<std::string,TargetRuntime> states_;
};
}