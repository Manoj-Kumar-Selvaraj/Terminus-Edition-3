#include "sovereign/snapshot.hpp"

#include <algorithm>
#include <arpa/inet.h>
#include <set>

namespace sovereign {

static int integer(const Json& object, const std::string& key, int minimum, int maximum) {
  auto value = object.at(key).integer();
  if (value < minimum || value > maximum) {
    throw JsonError(key + " out of range");
  }
  return static_cast<int>(value);
}

static std::string string(const Json& object, const std::string& key) {
  auto value = object.at(key).string();
  if (value.empty()) {
    throw JsonError(key + " is empty");
  }
  return value;
}

static bool boolean(const Json& object, const std::string& key) {
  return object.at(key).boolean();
}

static void address(const std::string& value) {
  in_addr v4{};
  in6_addr v6{};
  if (inet_pton(AF_INET, value.c_str(), &v4) != 1 && inet_pton(AF_INET6, value.c_str(), &v6) != 1) {
    throw JsonError("address is not an IP literal");
  }
}

static BalancePolicy balance(const std::string& value) {
  if (value == "round_robin") {
    return BalancePolicy::round_robin;
  }
  if (value == "least_connections") {
    return BalancePolicy::least_connections;
  }
  if (value == "source_hash") {
    return BalancePolicy::source_hash;
  }
  throw JsonError("invalid balancing policy");
}

static ZonePolicy zone_policy(const std::string& value) {
  if (value == "cross_zone") {
    return ZonePolicy::cross_zone;
  }
  if (value == "same_zone_preferred") {
    return ZonePolicy::same_zone_preferred;
  }
  throw JsonError("invalid zone policy");
}

static AdminState admin(const std::string& value) {
  if (value == "enabled") {
    return AdminState::enabled;
  }
  if (value == "disabled") {
    return AdminState::disabled;
  }
  if (value == "draining") {
    return AdminState::draining;
  }
  throw JsonError("invalid administrative state");
}

const TargetGroup& Snapshot::group(const std::string& name) const {
  auto found = group_index.find(name);
  if (found == group_index.end()) {
    throw JsonError("unknown target group");
  }
  return target_groups[found->second];
}

static Limits decode_limits(const Json& source) {
  Limits limits{};
  limits.max_listeners = integer(source, "max_listeners", 1, 1024);
  limits.max_target_groups = integer(source, "max_target_groups", 1, 1024);
  limits.max_targets = integer(source, "max_targets", 1, 65536);
  limits.max_frame_bytes = static_cast<std::uint32_t>(integer(source, "max_frame_bytes", 1, 16 << 20));
  limits.max_queue_messages = integer(source, "max_queue_messages", 1, 65536);
  limits.max_audit_events = integer(source, "max_audit_events", 1, 1 << 20);
  limits.retained_generations = integer(source, "retained_generations", 1, 256);
  limits.max_health_samples = integer(source, "max_health_samples", 1, 4096);
  limits.max_connection_records = integer(source, "max_connection_records", 1, 1 << 20);
  limits.max_buffer_bytes = static_cast<std::size_t>(integer(source, "max_buffer_bytes", 4096, 4 << 20));
  return limits;
}

std::shared_ptr<const Snapshot> decode_snapshot(const Json& value) {
  if (!value.is_object()) {
    throw JsonError("snapshot must be object");
  }
  auto result = std::make_shared<Snapshot>();
  result->generation = static_cast<std::uint64_t>(integer(value, "generation", 1, std::numeric_limits<int>::max()));
  result->revision = static_cast<std::uint64_t>(integer(value, "revision", 1, std::numeric_limits<int>::max()));
  result->created_at = string(value, "created_at");
  if (value.contains("limits")) {
    result->limits = decode_limits(value.at("limits"));
  }
  std::set<std::string> groups;
  for (const Json& source : value.at("target_groups").array()) {
    TargetGroup group;
    group.name = string(source, "name");
    if (!groups.insert(group.name).second) {
      throw JsonError("duplicate target group");
    }
    group.policy = balance(string(source, "policy"));
    group.zone_policy = zone_policy(string(source, "zone_policy"));
    group.fail_open = boolean(source, "fail_open");
    group.drain_timeout_ms = integer(source, "drain_timeout_ms", 1, 86400000);
    const Json& health = source.at("health");
    group.health = {
        integer(health, "interval_ms", 100, 3600000),
        integer(health, "timeout_ms", 1, 3600000),
        integer(health, "healthy_threshold", 1, 100),
        integer(health, "unhealthy_threshold", 1, 100),
        integer(health, "passive_failures", 1, 1000),
        integer(health, "passive_window_ms", 1, 3600000),
        integer(health, "ejection_ms", 1, 3600000),
        health.contains("send") ? health.at("send").string() : "",
        health.contains("expect") ? health.at("expect").string() : "",
    };
    std::set<std::string> identities;
    for (const Json& item : source.at("targets").array()) {
      Target target;
      target.id = string(item, "id");
      target.address = string(item, "address");
      address(target.address);
      target.port = static_cast<std::uint16_t>(integer(item, "port", 1, 65535));
      target.zone = string(item, "zone");
      target.administrative = admin(string(item, "administrative_state"));
      target.weight = integer(item, "weight", 1, 1000);
      target.incarnation = static_cast<std::uint64_t>(integer(item, "incarnation", 1, std::numeric_limits<int>::max()));
      target.identity = group.name + "/" + target.id + "/" + std::to_string(target.incarnation);
      if (!identities.insert(target.identity).second) {
        throw JsonError("duplicate target incarnation");
      }
      group.targets.push_back(std::move(target));
    }
    if (group.targets.empty()) {
      throw JsonError("target group is empty");
    }
    std::sort(group.targets.begin(), group.targets.end(), [](const Target& left, const Target& right) {
      return left.identity < right.identity;
    });
    result->group_index.emplace(group.name, result->target_groups.size());
    result->target_groups.push_back(std::move(group));
  }
  std::set<std::string> names;
  std::set<std::string> binds;
  for (const Json& source : value.at("listeners").array()) {
    Listener listener;
    listener.name = string(source, "name");
    listener.address = string(source, "address");
    address(listener.address);
    listener.port = static_cast<std::uint16_t>(integer(source, "port", 1, 65535));
    listener.target_group = string(source, "target_group");
    listener.proxy_protocol_v2 = boolean(source, "proxy_protocol_v2");
    listener.connect_timeout_ms = integer(source, "connect_timeout_ms", 1, 3600000);
    listener.idle_timeout_ms = integer(source, "idle_timeout_ms", 1, 86400000);
    listener.buffer_bytes = static_cast<std::size_t>(integer(source, "buffer_bytes", 4096, 4 << 20));
    if (!names.insert(listener.name).second) {
      throw JsonError("duplicate listener");
    }
    if (!binds.insert(listener.address + ":" + std::to_string(listener.port)).second) {
      throw JsonError("duplicate listener bind");
    }
    result->group(listener.target_group);
    result->listeners.push_back(std::move(listener));
  }
  if (result->listeners.empty()) {
    throw JsonError("snapshot has no listeners");
  }
  return result;
}

std::shared_ptr<const Snapshot> RuntimeStore::prepared() const {
  std::lock_guard lock(mutex_);
  return prepared_;
}

void RuntimeStore::prepare(std::shared_ptr<const Snapshot> candidate, std::string digest) {
  if (!candidate || digest.size() != 64) {
    throw JsonError("invalid candidate");
  }
  std::lock_guard lock(mutex_);
  if (prepared_ && prepared_->generation == candidate->generation && digest_ != digest) {
    throw JsonError("generation digest conflict");
  }
  prepared_ = std::move(candidate);
  digest_ = std::move(digest);
}

bool RuntimeStore::activate(std::uint64_t generation, const std::string& digest) {
  std::lock_guard lock(mutex_);
  if (!prepared_ || prepared_->generation != generation || digest_ != digest) {
    return false;
  }
  active_.store(prepared_);
  prepared_.reset();
  digest_.clear();
  return true;
}

std::string RuntimeStore::prepared_digest() const {
  std::lock_guard lock(mutex_);
  return digest_;
}

}  // namespace sovereign
