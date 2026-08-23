#include "sovereign/prober.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <thread>
#include <unistd.h>

namespace sovereign {
static int open_probe_socket(const Target& target) {
  const bool ipv6 = target.address.find(':') != std::string::npos;
  const int family = ipv6 ? AF_INET6 : AF_INET;
  int descriptor = socket(family, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (descriptor < 0) return -1;
  int flags = fcntl(descriptor, F_GETFL, 0);
  if (flags < 0 || fcntl(descriptor, F_SETFL, flags | O_NONBLOCK) < 0) {
    close(descriptor);
    return -1;
  }
  int result = -1;
  if (ipv6) {
    sockaddr_in6 endpoint{};
    endpoint.sin6_family = AF_INET6;
    endpoint.sin6_port = htons(target.port);
    if (inet_pton(AF_INET6, target.address.c_str(), &endpoint.sin6_addr) == 1) {
      result = connect(descriptor, reinterpret_cast<sockaddr*>(&endpoint), sizeof(endpoint));
    }
  } else {
    sockaddr_in endpoint{};
    endpoint.sin_family = AF_INET;
    endpoint.sin_port = htons(target.port);
    if (inet_pton(AF_INET, target.address.c_str(), &endpoint.sin_addr) == 1) {
      result = connect(descriptor, reinterpret_cast<sockaddr*>(&endpoint), sizeof(endpoint));
    }
  }
  if (result < 0 && errno != EINPROGRESS) {
    close(descriptor);
    return -1;
  }
  return descriptor;
}

bool ActiveProber::probe(const Target& target, const HealthPolicy& policy) const {
  int descriptor = open_probe_socket(target);
  if (descriptor < 0) return false;
  pollfd event{descriptor, POLLOUT, 0};
  int result = poll(&event, 1, policy.timeout_ms);
  if (result <= 0 || (event.revents & (POLLERR | POLLHUP | POLLNVAL))) {
    close(descriptor);
    return false;
  }
  int socket_error = 0;
  socklen_t error_size = sizeof(socket_error);
  if (getsockopt(descriptor, SOL_SOCKET, SO_ERROR, &socket_error, &error_size) < 0 || socket_error != 0) {
    close(descriptor);
    return false;
  }
  if (!policy.send.empty()) {
    ssize_t sent = send(descriptor, policy.send.data(), policy.send.size(), MSG_NOSIGNAL);
    if (sent != static_cast<ssize_t>(policy.send.size())) {
      close(descriptor);
      return false;
    }
  }
  bool healthy = true;
  if (!policy.expect.empty()) {
    std::string received(policy.expect.size(), '\0');
    pollfd readable{descriptor, POLLIN, 0};
    if (poll(&readable, 1, policy.timeout_ms) <= 0) {
      healthy = false;
    } else {
      ssize_t count = recv(descriptor, received.data(), received.size(), MSG_WAITALL);
      healthy = count == static_cast<ssize_t>(received.size()) && received == policy.expect;
    }
  }
  close(descriptor);
  return healthy;
}

void ActiveProber::refresh(const std::shared_ptr<const Snapshot>& snapshot,
                           std::chrono::steady_clock::time_point now) {
  while (!due_.empty()) due_.pop();
  if (!snapshot) return;
  for (const auto& group : snapshot->target_groups) {
    for (const auto& target : group.targets) {
      due_.push(Due{now, target.identity, snapshot->generation});
    }
  }
  scheduled_generation_ = snapshot->generation;
}

const std::pair<const Target*, const HealthPolicy*> ActiveProber::locate(
    const Snapshot& snapshot, const std::string& identity) const {
  for (const auto& group : snapshot.target_groups) {
    for (const auto& target : group.targets) {
      if (target.identity == identity) return {&target, &group.health};
    }
  }
  return {nullptr, nullptr};
}

void ActiveProber::run(std::atomic_bool& stopping) {
  while (!stopping.load()) {
    auto snapshot = runtimes_.active();
    auto now = std::chrono::steady_clock::now();
    if (snapshot && snapshot->generation != scheduled_generation_) refresh(snapshot, now);
    if (!snapshot || due_.empty()) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
      continue;
    }
    if (due_.top().at > now) {
      auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(due_.top().at - now);
      auto delay = remaining < std::chrono::milliseconds(100) ? remaining : std::chrono::milliseconds(100);
      std::this_thread::sleep_for(delay);
      continue;
    }
    Due item = due_.top();
    due_.pop();
    if (item.generation != snapshot->generation) continue;
    auto [target, policy] = locate(*snapshot, item.identity);
    if (!target || !policy) continue;
    bool success = probe(*target, *policy);
    tracker_.active_result(*target, *policy, success, std::chrono::steady_clock::now());
    due_.push(Due{std::chrono::steady_clock::now() + std::chrono::milliseconds(policy->interval_ms),
                  item.identity, item.generation});
  }
}
}