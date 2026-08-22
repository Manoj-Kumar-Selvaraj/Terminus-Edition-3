#pragma once
#include "sovereign/eligibility.hpp"
#include <mutex>
#include <optional>
#include <unordered_map>
namespace sovereign {
class Selector { public: const Target* select(const TargetGroup& group,const std::vector<const Target*>& candidates,const std::string& source,const Eligibility& eligibility); private: std::mutex mutex_; std::unordered_map<std::string,std::uint64_t> cursors_; static std::uint64_t stable_hash(const std::string& value); };
}