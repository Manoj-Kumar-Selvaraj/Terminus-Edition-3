#pragma once

#include <filesystem>

namespace stonevault {

class WriterLock {
public:
    explicit WriterLock(const std::filesystem::path& path);
    WriterLock(const WriterLock&) = delete;
    WriterLock& operator=(const WriterLock&) = delete;
    WriterLock(WriterLock&&) = delete;
    WriterLock& operator=(WriterLock&&) = delete;
    ~WriterLock();

private:
    int fd_{-1};
};

}  // namespace stonevault
