#pragma once
#include "sovereign/connection.hpp"
#include "sovereign/selector.hpp"
#include <atomic>
#include <unordered_map>
namespace sovereign {
class Proxy {
 public:
  Proxy(RuntimeStore& runtimes,Eligibility& eligibility,std::string zone,std::size_t maximum_connections);
  ~Proxy();
  void run(std::atomic_bool& stopping);
  void publish();
  void stop_accepting();
  ConnectionRegistry& connections(){return connections_;}
 private:
  void reconcile_listeners(); void accept_client(int descriptor); int connect_target(const Target& target); void handle(int descriptor,std::uint32_t events); bool transfer_read(int source,ByteBuffer& buffer,bool& closed); bool transfer_write(int destination,ByteBuffer& buffer); void update_interest(const std::shared_ptr<Connection>& connection); void close_connection(const std::shared_ptr<Connection>& connection); void expire();
  RuntimeStore& runtimes_;Eligibility& eligibility_;Selector selector_;std::string zone_;int epoll_fd_{-1};bool accepting_{true};ConnectionRegistry connections_;std::unordered_map<int,std::pair<std::shared_ptr<const Snapshot>,const Listener*>> listeners_;
};
}