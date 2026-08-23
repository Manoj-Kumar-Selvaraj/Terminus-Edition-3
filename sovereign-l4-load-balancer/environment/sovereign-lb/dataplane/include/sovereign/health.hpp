#pragma once
#include "sovereign/eligibility.hpp"
#include <deque>
#include <mutex>
namespace sovereign {
class HealthTracker { public: explicit HealthTracker(Eligibility& eligibility):eligibility_(eligibility){} void active_result(const Target& target,const HealthPolicy& policy,bool success,std::chrono::steady_clock::time_point now); void passive_failure(const Target& target,const HealthPolicy& policy,std::chrono::steady_clock::time_point now); void begin_drain(const Target& target,std::chrono::milliseconds timeout,std::chrono::steady_clock::time_point now); private: struct History{int successes{};int failures{};std::deque<std::chrono::steady_clock::time_point> passive;};Eligibility& eligibility_;std::mutex mutex_;std::unordered_map<std::string,History> history_; };
}