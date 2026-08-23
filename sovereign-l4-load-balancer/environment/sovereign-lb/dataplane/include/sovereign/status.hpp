#pragma once
#include "sovereign/connection.hpp"
#include "sovereign/snapshot.hpp"
#include <atomic>
#include <map>
#include <mutex>
#include <string>
namespace sovereign {
class Counters { public: void increment(const std::string& name); std::string prometheus() const; private: mutable std::mutex mutex_;std::map<std::string,std::uint64_t> values_; };
class StatusServer { public: StatusServer(RuntimeStore& runtimes,ConnectionRegistry& connections,Counters& counters):runtimes_(runtimes),connections_(connections),counters_(counters){} void serve(const std::string& address,std::atomic_bool& stopping); private: std::string response(const std::string& path)const;RuntimeStore& runtimes_;ConnectionRegistry& connections_;Counters& counters_; };
}