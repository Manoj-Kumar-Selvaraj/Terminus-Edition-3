#include "maintenance.hpp"

#include <cerrno>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <system_error>

namespace stonevault {

StoragePaths prepare_storage_paths(const std::filesystem::path& directory) {
    if (directory.empty()) {
        throw std::runtime_error("data directory is required");
    }

    std::error_code error;
    std::filesystem::create_directories(directory, error);
    if (error) {
        throw std::runtime_error(
            "cannot create data directory: " + error.message());
    }
    validate_data_directory(directory);

    return StoragePaths{
        directory,
        directory / "LOCK",
        directory / "wal.log",
        directory / "snapshot.dat",
    };
}

void validate_data_directory(const std::filesystem::path& directory) {
    std::error_code error;
    const auto status = std::filesystem::status(directory, error);
    if (error) {
        throw std::runtime_error(
            "cannot inspect data directory: " + error.message());
    }
    if (!std::filesystem::is_directory(status)) {
        throw std::runtime_error("data path is not a directory");
    }

    const auto probe = directory / ".stonevault-write-probe";
    {
        std::ofstream out(probe, std::ios::binary | std::ios::trunc);
        if (!out) {
            throw std::runtime_error("data directory is not writable");
        }
        out << "probe";
        if (!out) {
            throw std::runtime_error("cannot write data directory probe");
        }
    }
    std::filesystem::remove(probe, error);
    if (error) {
        throw std::runtime_error(
            "cannot remove data directory probe: " + error.message());
    }
}

std::string render_stats(
    std::uint64_t commit_sequence,
    std::uint64_t visible_keys,
    std::uint64_t wal_bytes) {
    return "commit_seq=" + std::to_string(commit_sequence) +
        " keys=" + std::to_string(visible_keys) +
        " wal_bytes=" + std::to_string(wal_bytes);
}

}  // namespace stonevault
