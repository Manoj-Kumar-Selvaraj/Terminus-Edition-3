#include "integrity.hpp"

#include <filesystem>
#include <sstream>
#include <stdexcept>
#include <system_error>

namespace stonevault {

namespace {

void require_regular_or_missing(
    const std::filesystem::path& path,
    const char* label) {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    if (error) {
        if (error == std::errc::no_such_file_or_directory) {
            return;
        }
        throw std::runtime_error(
            std::string("cannot inspect ") + label + ": " + error.message());
    }
    if (status.type() == std::filesystem::file_type::not_found) {
        return;
    }
    if (status.type() != std::filesystem::file_type::regular) {
        throw std::runtime_error(
            std::string(label) + " must be a regular file");
    }
}

}  // namespace

void validate_catalog_integrity(
    const VersionCatalog& catalog,
    std::uint64_t commit_sequence) {
    // The public catalog API intentionally exposes only stable derived views.
    // Reconstructing a snapshot here exercises ordering, tombstone resolution,
    // and visibility consistency without reaching into the catalog internals.
    const SnapshotImage image = catalog.snapshot_image(commit_sequence);
    if (image.sequence != commit_sequence) {
        throw std::runtime_error("catalog integrity: sequence mismatch");
    }

    ByteLess less;
    bool first = true;
    std::string previous;
    std::uint64_t visible = 0;
    for (const auto& [key, value] : image.rows) {
        if (!first && !less(previous, key)) {
            throw std::runtime_error(
                "catalog integrity: keys are not strictly ordered");
        }
        const auto resolved = catalog.visible_value(key, commit_sequence);
        if (!resolved.has_value() || *resolved != value) {
            throw std::runtime_error(
                "catalog integrity: snapshot visibility mismatch");
        }
        previous = key;
        first = false;
        ++visible;
    }

    if (visible != catalog.visible_key_count(commit_sequence)) {
        throw std::runtime_error(
            "catalog integrity: visible key count mismatch");
    }
}

void validate_storage_paths(const StoragePaths& paths) {
    std::error_code error;
    const auto directory_status =
        std::filesystem::symlink_status(paths.directory, error);
    if (error) {
        throw std::runtime_error(
            "cannot inspect data directory: " + error.message());
    }
    if (directory_status.type() != std::filesystem::file_type::directory) {
        throw std::runtime_error("data directory is not a directory");
    }

    require_regular_or_missing(paths.lock, "LOCK");
    require_regular_or_missing(paths.wal, "wal.log");
    require_regular_or_missing(paths.snapshot, "snapshot.dat");
    require_regular_or_missing((paths.directory / "snapshot.tmp"), "snapshot.tmp");
}

std::string render_health(const IntegrityReport& report) {
    std::ostringstream output;
    output << "status=ok"
           << " commit_seq=" << report.commit_sequence
           << " keys=" << report.visible_keys
           << " active_tx=" << report.active_transactions
           << " wal_bytes=" << report.wal_bytes
           << " snapshot=" << (report.snapshot_present ? "present" : "absent");
    return output.str();
}

}  // namespace stonevault
