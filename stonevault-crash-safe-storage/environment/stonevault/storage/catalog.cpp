#include "catalog.hpp"

#include <algorithm>
#include <stdexcept>

namespace stonevault {

void VersionCatalog::load_snapshot(const SnapshotImage& image) {
    versions_.clear();
    for (const auto& row : image.rows) {
        if (row.key.size() > kMaxKeyBytes) {
            throw std::runtime_error("snapshot key exceeds catalog limit");
        }
        if (row.value.size() > kMaxValueBytes) {
            throw std::runtime_error("snapshot value exceeds catalog limit");
        }
        versions_[row.key].push_back(Version{image.sequence, false, row.value});
    }
}

void VersionCatalog::apply_commit(const OrderedValues& writes, std::uint64_t sequence) {
    if (sequence == 0) {
        throw std::runtime_error("commit sequence must be positive");
    }
    for (const auto& [key, value] : writes) {
        if (key.size() > kMaxKeyBytes) {
            throw std::runtime_error("commit key exceeds catalog limit");
        }
        if (value.has_value() && value->size() > kMaxValueBytes) {
            throw std::runtime_error("commit value exceeds catalog limit");
        }
        auto& history = versions_[key];
        if (!history.empty() && history.back().sequence >= sequence) {
            throw std::runtime_error("catalog commit sequence is not increasing");
        }
        if (value.has_value()) {
            history.push_back(Version{sequence, false, *value});
        } else {
            history.push_back(Version{sequence, true, {}});
        }
    }
}

std::optional<std::string> VersionCatalog::visible_value(
    const std::string& key,
    std::uint64_t snapshot) const {
    const auto found = versions_.find(key);
    if (found == versions_.end()) {
        return std::nullopt;
    }
    return visible_from_versions(found->second, snapshot);
}

OrderedValues VersionCatalog::scan(const std::string& prefix, std::uint64_t snapshot) const {
    OrderedValues rows;
    for (const auto& [key, history] : versions_) {
        if (!starts_with(key, prefix)) {
            continue;
        }
        auto value = visible_from_versions(history, snapshot);
        if (value.has_value()) {
            rows[key] = *value;
        }
    }
    return rows;
}

bool VersionCatalog::conflicts(const OrderedValues& writes, std::uint64_t snapshot) const {
    for (const auto& [key, _] : writes) {
        if (latest_sequence_for(key) > snapshot) {
            return true;
        }
    }
    return false;
}

std::size_t VersionCatalog::visible_key_count(std::uint64_t snapshot) const {
    std::size_t count = 0;
    for (const auto& [_, history] : versions_) {
        if (visible_from_versions(history, snapshot).has_value()) {
            ++count;
        }
    }
    return count;
}

SnapshotImage VersionCatalog::snapshot_image(std::uint64_t sequence) const {
    SnapshotImage image;
    image.sequence = sequence;
    image.rows.reserve(versions_.size());
    for (const auto& [key, history] : versions_) {
        auto value = visible_from_versions(history, sequence);
        if (value.has_value()) {
            image.rows.push_back(SnapshotRow{key, *value});
        }
    }
    return image;
}

std::uint64_t VersionCatalog::latest_sequence_for(const std::string& key) const {
    const auto found = versions_.find(key);
    if (found == versions_.end() || found->second.empty()) {
        return 0;
    }
    return found->second.back().sequence;
}

CatalogAudit VersionCatalog::audit(std::uint64_t committed_sequence) const {
    CatalogAudit audit;
    ByteLess less;
    bool first_key = true;
    std::string previous_key;

    for (const auto& [key, history] : versions_) {
        if (key.size() > kMaxKeyBytes) {
            throw std::runtime_error("catalog integrity: key exceeds configured limit");
        }
        if (!first_key && !less(previous_key, key)) {
            throw std::runtime_error("catalog integrity: key order is not strictly increasing");
        }
        if (history.empty()) {
            throw std::runtime_error("catalog integrity: key has empty version history");
        }

        ++audit.key_histories;
        audit.max_history_depth = std::max(audit.max_history_depth, history.size());
        if (history.size() > 1) {
            ++audit.multi_version_histories;
        }
        if (history.back().tombstone) {
            ++audit.tombstoned_histories;
        }
        std::uint64_t previous_sequence = 0;
        bool first_version = true;
        for (const auto& version : history) {
            if (!first_version && version.sequence <= previous_sequence) {
                throw std::runtime_error("catalog integrity: version sequence is not increasing");
            }
            if (version.sequence > committed_sequence) {
                throw std::runtime_error("catalog integrity: version is newer than committed state");
            }
            if (version.tombstone) {
                if (!version.value.empty()) {
                    throw std::runtime_error("catalog integrity: tombstone carries a value");
                }
                ++audit.tombstone_versions;
            } else {
                if (version.value.size() > kMaxValueBytes) {
                    throw std::runtime_error("catalog integrity: value exceeds configured limit");
                }
                ++audit.value_versions;
            }

            ++audit.total_versions;
            audit.max_sequence = std::max(audit.max_sequence, version.sequence);
            previous_sequence = version.sequence;
            first_version = false;
        }

        if (visible_from_versions(history, committed_sequence).has_value()) {
            ++audit.visible_keys;
        }
        previous_key = key;
        first_key = false;
    }

    if (audit.visible_keys != visible_key_count(committed_sequence)) {
        throw std::runtime_error("catalog integrity: visible-key accounting mismatch");
    }
    if (audit.key_histories != versions_.size()) {
        throw std::runtime_error("catalog integrity: history accounting mismatch");
    }
    if (audit.value_versions + audit.tombstone_versions != audit.total_versions) {
        throw std::runtime_error("catalog integrity: version accounting mismatch");
    }
    if (audit.max_history_depth > audit.total_versions && audit.total_versions != 0) {
        throw std::runtime_error("catalog integrity: invalid history depth accounting");
    }
    if (audit.max_sequence > committed_sequence) {
        throw std::runtime_error("catalog integrity: maximum sequence exceeds committed state");
    }
    return audit;
}

std::optional<std::string> VersionCatalog::visible_from_versions(
    const std::vector<Version>& versions,
    std::uint64_t snapshot) {
    for (auto it = versions.rbegin(); it != versions.rend(); ++it) {
        if (it->sequence <= snapshot) {
            if (it->tombstone) {
                return std::nullopt;
            }
            return it->value;
        }
    }
    return std::nullopt;
}

bool VersionCatalog::starts_with(const std::string& value, const std::string& prefix) {
    return value.size() >= prefix.size() &&
        std::equal(prefix.begin(), prefix.end(), value.begin());
}

}  // namespace stonevault
