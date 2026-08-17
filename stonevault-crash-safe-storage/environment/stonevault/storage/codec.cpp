#include "codec.hpp"

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace stonevault::codec {

std::uint32_t crc32(const unsigned char* data, std::size_t length) {
    static std::uint32_t table[256]{};
    static bool initialized = false;
    if (!initialized) {
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t value = i;
            for (int bit = 0; bit < 8; ++bit) {
                value = (value & 1U) ? (0xEDB88320U ^ (value >> 1U)) : (value >> 1U);
            }
            table[i] = value;
        }
        initialized = true;
    }

    std::uint32_t value = 0xFFFFFFFFU;
    for (std::size_t i = 0; i < length; ++i) {
        value = table[(value ^ data[i]) & 0xFFU] ^ (value >> 8U);
    }
    return value ^ 0xFFFFFFFFU;
}

std::uint32_t crc32(const std::vector<unsigned char>& data) {
    return crc32(data.data(), data.size());
}

void append_u32(std::vector<unsigned char>& out, std::uint32_t value) {
    for (int shift = 0; shift < 32; shift += 8) {
        out.push_back(static_cast<unsigned char>((value >> shift) & 0xFFU));
    }
}

void append_u64(std::vector<unsigned char>& out, std::uint64_t value) {
    for (int shift = 0; shift < 64; shift += 8) {
        out.push_back(static_cast<unsigned char>((value >> shift) & 0xFFU));
    }
}

bool read_u32(const std::vector<unsigned char>& in, std::size_t& pos, std::uint32_t& value) {
    if (pos > in.size() || in.size() - pos < 4) {
        return false;
    }
    value = 0;
    for (int shift = 0; shift < 32; shift += 8) {
        value |= static_cast<std::uint32_t>(in[pos++]) << shift;
    }
    return true;
}

bool read_u64(const std::vector<unsigned char>& in, std::size_t& pos, std::uint64_t& value) {
    if (pos > in.size() || in.size() - pos < 8) {
        return false;
    }
    value = 0;
    for (int shift = 0; shift < 64; shift += 8) {
        value |= static_cast<std::uint64_t>(in[pos++]) << shift;
    }
    return true;
}

std::optional<std::string> hex_decode(const char* text) {
    if (text == nullptr) {
        return std::nullopt;
    }
    const std::string hex(text);
    if ((hex.size() & 1U) != 0U) {
        return std::nullopt;
    }

    auto nibble = [](char value) -> int {
        if (value >= '0' && value <= '9') return value - '0';
        if (value >= 'a' && value <= 'f') return 10 + value - 'a';
        if (value >= 'A' && value <= 'F') return 10 + value - 'A';
        return -1;
    };

    std::string bytes(hex.size() / 2, '\0');
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        const int hi = nibble(hex[2 * i]);
        const int lo = nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) {
            return std::nullopt;
        }
        bytes[i] = static_cast<char>((hi << 4) | lo);
    }
    return bytes;
}

std::string hex_encode(const std::string& bytes) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string output;
    output.reserve(bytes.size() * 2);
    for (unsigned char byte : bytes) {
        output.push_back(digits[byte >> 4]);
        output.push_back(digits[byte & 0x0FU]);
    }
    return output;
}

bool write_all(int fd, const unsigned char* data, std::size_t length) {
    while (length > 0) {
        const ssize_t written = ::write(fd, data, length);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        if (written == 0) {
            errno = EIO;
            return false;
        }
        data += static_cast<std::size_t>(written);
        length -= static_cast<std::size_t>(written);
    }
    return true;
}

bool write_all(int fd, const std::vector<unsigned char>& data) {
    if (data.empty()) {
        return true;
    }
    return write_all(fd, data.data(), data.size());
}

std::vector<unsigned char> read_file(const std::filesystem::path& path) {
    int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        if (errno == ENOENT) {
            return {};
        }
        throw std::runtime_error(errno_message("cannot open " + path.string()));
    }

    struct stat state{};
    if (::fstat(fd, &state) != 0) {
        const std::string message = errno_message("cannot stat " + path.string());
        ::close(fd);
        throw std::runtime_error(message);
    }

    std::vector<unsigned char> bytes(static_cast<std::size_t>(state.st_size));
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        const ssize_t received = ::read(fd, bytes.data() + offset, bytes.size() - offset);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            const std::string message = errno_message("cannot read " + path.string());
            ::close(fd);
            throw std::runtime_error(message);
        }
        if (received == 0) {
            break;
        }
        offset += static_cast<std::size_t>(received);
    }
    ::close(fd);
    bytes.resize(offset);
    return bytes;
}

std::uint64_t file_size(int fd) {
    struct stat state{};
    if (::fstat(fd, &state) != 0) {
        throw std::runtime_error(errno_message("cannot stat file"));
    }
    return static_cast<std::uint64_t>(state.st_size);
}

void sync_fd(int fd, bool data_only, const std::string& what) {
    const int result = data_only ? ::fdatasync(fd) : ::fsync(fd);
    if (result != 0) {
        throw std::runtime_error(errno_message("cannot sync " + what));
    }
}

void sync_directory(const std::filesystem::path& directory) {
    int fd = ::open(directory.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) {
        throw std::runtime_error(errno_message("cannot open directory for sync"));
    }
    if (::fsync(fd) != 0) {
        const std::string message = errno_message("cannot sync directory");
        ::close(fd);
        throw std::runtime_error(message);
    }
    ::close(fd);
}

std::string errno_message(const std::string& prefix) {
    return prefix + ": " + std::strerror(errno);
}

}  // namespace stonevault::codec
