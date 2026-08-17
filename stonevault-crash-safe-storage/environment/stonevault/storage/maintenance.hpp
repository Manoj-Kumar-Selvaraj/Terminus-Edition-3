#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

namespace stonevault {

struct StoragePaths {
    std::filesystem::path directory;
    std::filesystem::path lock;
    std::filesystem::path wal;
    std::filesystem::path snapshot;
};

StoragePaths prepare_storage_paths(const std::filesystem::path& directory);
void validate_data_directory(const std::filesystem::path& directory);
std::string render_stats(
    std::uint64_t commit_sequence,
    std::uint64_t visible_keys,
    std::uint64_t wal_bytes);

}  // namespace stonevault
