#pragma once
#include "sovereign/json.hpp"
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace sovereign {
enum class BalancePolicy { round_robin, least_connections, source_hash };
enum class ZonePolicy { cross_zone, same_zone_preferred };
enum class AdminState { enabled, disabled, draining };
struct HealthPolicy { int interval_ms{}; int timeout_ms{}; int healthy_threshold{}; int unhealthy_threshold{}; int passive_failures{}; int passive_window_ms{}; int ejection_ms{}; std::string send; std::string expect; };
struct Target { std::string id; std::string address; std::uint16_t port{}; std::string zone; AdminState administrative{AdminState::enabled}; int weight{1}; std::uint64_t incarnation{}; std::string identity; };
struct TargetGroup { std::string name; BalancePolicy policy{BalancePolicy::round_robin}; ZonePolicy zone_policy{ZonePolicy::cross_zone}; bool fail_open{}; int drain_timeout_ms{}; HealthPolicy health; std::vector<Target> targets; };
struct Listener { std::string name; std::string address; std::uint16_t port{}; std::string target_group; bool proxy_protocol_v2{}; int connect_timeout_ms{}; int idle_timeout_ms{}; std::size_t buffer_bytes{}; };
struct Limits {
  int max_listeners{};
  int max_target_groups{};
  int max_targets{};
  std::uint32_t max_frame_bytes{};
  int max_queue_messages{};
  int max_audit_events{};
  int retained_generations{};
  int max_health_samples{};
  int max_connection_records{};
  std::size_t max_buffer_bytes{};
};
struct Snapshot {
  std::uint64_t generation{};
  std::uint64_t revision{};
  std::string created_at;
  std::vector<Listener> listeners;
  std::vector<TargetGroup> target_groups;
  Limits limits{};
  std::unordered_map<std::string, std::size_t> group_index;
  const TargetGroup& group(const std::string& name) const;
};
std::shared_ptr<const Snapshot> decode_snapshot(const Json& value);

class RuntimeStore {
 public:
  std::shared_ptr<const Snapshot> active() const { return active_.load(); }
  std::shared_ptr<const Snapshot> prepared() const;
  void prepare(std::shared_ptr<const Snapshot> candidate, std::string digest);
  bool activate(std::uint64_t generation, const std::string& digest);
  std::string prepared_digest() const;
 private:
  std::atomic<std::shared_ptr<const Snapshot>> active_{};
  mutable std::mutex mutex_; std::shared_ptr<const Snapshot> prepared_; std::string digest_;
};
}