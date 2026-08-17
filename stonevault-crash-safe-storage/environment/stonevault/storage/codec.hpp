#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace stonevault::codec {

std::uint32_t crc32(const unsigned char* data, std::size_t length);
std::uint32_t crc32(const std::vector<unsigned char>& data);

void append_u32(std::vector<unsigned char>& out, std::uint32_t value);
void append_u64(std::vector<unsigned char>& out, std::uint64_t value);

bool read_u32(const std::vector<unsigned char>& in, std::size_t& pos, std::uint32_t& value);
bool read_u64(const std::vector<unsigned char>& in, std::size_t& pos, std::uint64_t& value);

std::optional<std::string> hex_decode(const char* text);
std::string hex_encode(const std::string& bytes);

bool write_all(int fd, const unsigned char* data, std::size_t length);
bool write_all(int fd, const std::vector<unsigned char>& data);

std::vector<unsigned char> read_file(const std::filesystem::path& path);
std::uint64_t file_size(int fd);
void sync_fd(int fd, bool data_only, const std::string& what);
void sync_directory(const std::filesystem::path& directory);

std::string errno_message(const std::string& prefix);

}  // namespace stonevault::codec
