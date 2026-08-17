#include "integrity.hpp"

#include <cerrno>
#include <filesystem>
#include <sstream>
#include <stdexcept>
#include <system_error>

namespace stonevault {

namespace {

struct InspectedPath {
    bool present{};
    std::uint64_t bytes{};
};

InspectedPath inspect_regular_or_missing(
    const std::filesystem::path& path,
    const char* label) {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    if (error) {
        if (error == std::errc::no_such_file_or_directory) {
            return {};
        }
        throw std::runtime_error(
            std::string("cannot inspect ") + label + ": " + error.message());
    }
    if (status.type() == std::filesystem::file_type::not_found) {
        return {};
    }
    if (status.type() != std::filesystem::file_type::regular) {
        throw std::runtime_error(std::string(label) + " must be a regular file");
    }

    const auto size = std::filesystem::file_size(path, error);
    if (error) {
        throw std::runtime_error(
            std::string("cannot size ") + label + ": " + error.message());
    }
    return InspectedPath{true, static_cast<std::uint64_t>(size)};
}

void validate_storage_relationships(
    const StoragePaths& paths,
    const StoragePathAudit& audit) {
    if (!audit.lock_present) {
        throw std::runtime_error("storage integrity: LOCK is missing while engine is open");
    }
    if (!audit.wal_present) {
        throw std::runtime_error("storage integrity: wal.log is missing while engine is open");
    }
    if (paths.lock == paths.wal ||
        paths.lock == paths.snapshot ||
        paths.wal == paths.snapshot) {
        throw std::runtime_error("storage integrity: durable paths alias one another");
    }
    if (audit.snapshot_temporary_present && paths.snapshot == paths.directory / "snapshot.tmp") {
        throw std::runtime_error("storage integrity: published and temporary snapshot paths alias");
    }
}

}  // namespace

CatalogAudit validate_catalog_integrity(
    const VersionCatalog& catalog,
    std::uint64_t commit_sequence) {
    const CatalogAudit audit = catalog.audit(commit_sequence);
    const SnapshotImage image = catalog.snapshot_image(commit_sequence);
    if (image.sequence != commit_sequence) {
        throw std::runtime_error("catalog integrity: sequence mismatch");
    }
    if (image.rows.size() != audit.visible_keys) {
        throw std::runtime_error("catalog integrity: snapshot row accounting mismatch");
    }

    ByteLess less;
    bool first = true;
    std::string previous;
    for (const auto& [key, value] : image.rows) {
        if (!first && !less(previous, key)) {
            throw std::runtime_error("catalog integrity: snapshot keys are not strictly ordered");
        }
        const auto resolved = catalog.visible_value(key, commit_sequence);
        if (!resolved.has_value() || *resolved != value) {
            throw std::runtime_error("catalog integrity: snapshot visibility mismatch");
        }
        previous = key;
        first = false;
    }
    return audit;
}

TransactionAudit validate_transaction_integrity(
    const TransactionTable& transactions,
    std::uint64_t commit_sequence) {
    const TransactionAudit audit = transactions.audit(commit_sequence);
    if (audit.active_transactions != transactions.size()) {
        throw std::runtime_error("transaction integrity: active-count mismatch");
    }
    if (transactions.empty() != (audit.active_transactions == 0)) {
        throw std::runtime_error("transaction integrity: empty-state mismatch");
    }
    if (audit.active_transactions > 0 &&
        audit.oldest_snapshot > audit.newest_snapshot) {
        throw std::runtime_error("transaction integrity: snapshot range is inverted");
    }
    return audit;
}

StoragePathAudit validate_storage_paths(const StoragePaths& paths) {
    std::error_code error;
    const auto directory_status = std::filesystem::symlink_status(paths.directory, error);
    if (error) {
        throw std::runtime_error("cannot inspect data directory: " + error.message());
    }
    if (directory_status.type() != std::filesystem::file_type::directory) {
        throw std::runtime_error("data directory is not a directory");
    }

    const InspectedPath lock = inspect_regular_or_missing(paths.lock, "LOCK");
    const InspectedPath wal = inspect_regular_or_missing(paths.wal, "wal.log");
    const InspectedPath snapshot = inspect_regular_or_missing(paths.snapshot, "snapshot.dat");
    const InspectedPath temporary = inspect_regular_or_missing(
        paths.directory / "snapshot.tmp",
        "snapshot.tmp");

    StoragePathAudit audit{
        lock.present,
        wal.present,
        snapshot.present,
        temporary.present,
        lock.bytes,
        wal.bytes,
        snapshot.bytes,
        temporary.bytes,
    };
    validate_storage_relationships(paths, audit);
    return audit;
}

RuntimeAudit audit_runtime_state(
    const StoragePaths& paths,
    const VersionCatalog& catalog,
    const TransactionTable& transactions,
    std::uint64_t commit_sequence) {
    RuntimeAudit audit;
    audit.catalog = validate_catalog_integrity(catalog, commit_sequence);
    audit.transactions = validate_transaction_integrity(transactions, commit_sequence);
    audit.storage = validate_storage_paths(paths);

    if (audit.catalog.max_sequence > commit_sequence) {
        throw std::runtime_error("runtime integrity: catalog sequence exceeds engine sequence");
    }
    if (audit.transactions.newest_snapshot > commit_sequence) {
        throw std::runtime_error("runtime integrity: transaction snapshot exceeds engine sequence");
    }
    return audit;
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
