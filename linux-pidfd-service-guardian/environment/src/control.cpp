#include "guardian/control.hpp"

#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

namespace guardian {
namespace {

sockaddr_un socket_address(const std::filesystem::path& path) {
  const std::string text = path.string();
  if (text.empty() || text.size() >= sizeof(sockaddr_un::sun_path)) {
    throw Error("control socket path is too long");
  }
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  std::memcpy(address.sun_path, text.c_str(), text.size() + 1);
  return address;
}

void reject_existing_non_socket(const std::filesystem::path& path) {
  struct stat metadata {};
  if (::lstat(path.c_str(), &metadata) < 0) {
    if (errno == ENOENT) {
      return;
    }
    throw Error(errno_message("lstat control socket"));
  }
  if (!S_ISSOCK(metadata.st_mode)) {
    throw Error("control path exists and is not a socket");
  }
  if (::unlink(path.c_str()) < 0) {
    throw Error(errno_message("unlink stale control socket"));
  }
}

std::string receive_packet(int fd) {
  std::array<char, 8192> buffer{};
  const ssize_t count = ::recv(fd, buffer.data(), buffer.size(), 0);
  if (count < 0) {
    throw Error(errno_message("receive control request"));
  }
  if (count == 0) {
    return {};
  }
  if (static_cast<std::size_t>(count) == buffer.size()) {
    throw Error("control request is too large");
  }
  return trim(std::string_view(buffer.data(), static_cast<std::size_t>(count)));
}

void send_packet(int fd, std::string_view response) {
  const ssize_t count =
      ::send(fd, response.data(), response.size(), MSG_NOSIGNAL);
  if (count < 0 || static_cast<std::size_t>(count) != response.size()) {
    throw Error(errno_message("send control response"));
  }
}

}  // namespace

ControlServer::ControlServer(const std::filesystem::path& socket_path,
                             Handler handler)
    : socket_path_(socket_path), handler_(std::move(handler)) {
  reject_existing_non_socket(socket_path_);
  socket_.reset(::socket(AF_UNIX, SOCK_SEQPACKET | SOCK_NONBLOCK | SOCK_CLOEXEC,
                         0));
  if (!socket_.valid()) {
    throw Error(errno_message("create control socket"));
  }
  const sockaddr_un address = socket_address(socket_path_);
  if (::bind(socket_.get(), reinterpret_cast<const sockaddr*>(&address),
             sizeof(address)) < 0) {
    throw Error(errno_message("bind control socket"));
  }
  if (::chmod(socket_path_.c_str(), 0666) < 0) {
    throw Error(errno_message("chmod control socket"));
  }
  if (::listen(socket_.get(), 32) < 0) {
    throw Error(errno_message("listen control socket"));
  }
}

ControlServer::~ControlServer() {
  socket_.reset();
  if (!socket_path_.empty()) {
    ::unlink(socket_path_.c_str());
  }
}

int ControlServer::fd() const noexcept { return socket_.get(); }

void ControlServer::accept_one() {
  while (true) {
    UniqueFd client(::accept4(socket_.get(), nullptr, nullptr,
                              SOCK_CLOEXEC | SOCK_NONBLOCK));
    if (!client.valid()) {
      if (errno == EINTR) {
        continue;
      }
      if (errno == EAGAIN || errno == EWOULDBLOCK) {
        return;
      }
      throw Error(errno_message("accept control connection"));
    }

    ucred credentials{};
    socklen_t length = sizeof(credentials);
    if (::getsockopt(client.get(), SOL_SOCKET, SO_PEERCRED, &credentials,
                     &length) < 0) {
      send_packet(client.get(), "ERR|code=PEER_CREDENTIALS\n");
      continue;
    }
    if (credentials.uid != ::geteuid()) {
      send_packet(client.get(), "ERR|code=ACCESS_DENIED\n");
      continue;
    }
    const std::string request = receive_packet(client.get());
    if (request.empty()) {
      send_packet(client.get(), "ERR|code=EMPTY_REQUEST\n");
      continue;
    }
    std::string response;
    try {
      response = handler_(request);
    } catch (const std::exception&) {
      response = "ERR|code=INTERNAL\n";
    }
    if (response.empty() || response.back() != '\n') {
      response.push_back('\n');
    }
    send_packet(client.get(), response);
  }
}

std::string control_request(const std::filesystem::path& socket_path,
                            const std::string& request) {
  UniqueFd socket(::socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0));
  if (!socket.valid()) {
    throw Error(errno_message("create client socket"));
  }
  const sockaddr_un address = socket_address(socket_path);
  if (::connect(socket.get(), reinterpret_cast<const sockaddr*>(&address),
                sizeof(address)) < 0) {
    throw Error(errno_message("connect control socket"));
  }
  send_packet(socket.get(), request);
  return receive_packet(socket.get()) + "\n";
}

}  // namespace guardian
