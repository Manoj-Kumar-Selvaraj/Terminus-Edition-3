#pragma once
#include "sovereign/snapshot.hpp"
#include <chrono>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include <sys/socket.h>

namespace sovereign {
class ByteBuffer {
 public:
  explicit ByteBuffer(std::size_t capacity) : storage_(capacity) {}
  std::size_t readable() const { return size_; }
  std::size_t writable() const { return storage_.size()-size_; }
  std::pair<std::uint8_t*,std::size_t> write_span();
  std::pair<const std::uint8_t*,std::size_t> read_span() const;
  void produced(std::size_t amount);
  void consumed(std::size_t amount);
  bool append(const std::uint8_t* data,std::size_t size);
 private:
  std::vector<std::uint8_t> storage_; std::size_t read_{0}; std::size_t write_{0}; std::size_t size_{0};
};

enum class ConnectState { connecting, established, failed };
struct Connection {
  std::uint64_t id{}; int client_fd{-1}; int target_fd{-1}; std::shared_ptr<const Snapshot> snapshot; const Listener* listener{}; const Target* target{}; ByteBuffer client_to_target; ByteBuffer target_to_client; ConnectState connect_state{ConnectState::connecting}; bool client_read_closed{}; bool target_read_closed{}; bool client_write_closed{}; bool target_write_closed{}; bool proxy_header_pending{}; std::chrono::steady_clock::time_point accepted_at; std::chrono::steady_clock::time_point last_progress;
  Connection(std::uint64_t value,int client,std::shared_ptr<const Snapshot> runtime,const Listener* selected_listener,const Target* selected_target);
  bool complete() const;
};

class ConnectionRegistry {
 public:
  explicit ConnectionRegistry(std::size_t maximum) : maximum_(maximum) {}
  std::shared_ptr<Connection> add(int client,std::shared_ptr<const Snapshot> snapshot,const Listener* listener,const Target* target);
  std::shared_ptr<Connection> by_fd(int descriptor) const;
  void bind_target(const std::shared_ptr<Connection>& connection,int descriptor);
  void remove(std::uint64_t id);
  std::vector<std::shared_ptr<Connection>> snapshot(std::size_t limit) const;
  std::size_t size() const;
 private:
  std::size_t maximum_; mutable std::mutex mutex_; std::uint64_t next_{1}; std::unordered_map<std::uint64_t,std::shared_ptr<Connection>> values_; std::unordered_map<int,std::uint64_t> descriptors_;
};

std::vector<std::uint8_t> proxy_v2_header(const sockaddr_storage& source,const sockaddr_storage& destination);
}