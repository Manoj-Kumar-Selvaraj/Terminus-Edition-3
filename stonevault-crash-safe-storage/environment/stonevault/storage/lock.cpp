#include "lock.hpp"
#include "codec.hpp"

#include <cerrno>
#include <fcntl.h>
#include <stdexcept>
#include <sys/file.h>
#include <unistd.h>

namespace stonevault {

WriterLock::WriterLock(const std::filesystem::path& path) {
    fd_ = ::open(path.c_str(), O_CREAT | O_RDWR | O_CLOEXEC, 0644);
    if (fd_ < 0) {
        throw std::runtime_error(codec::errno_message("cannot open writer lock"));
    }
}

WriterLock::~WriterLock() {
    if (fd_ >= 0) {
        ::flock(fd_, LOCK_UN);
        ::close(fd_);
    }
}

}  // namespace stonevault
