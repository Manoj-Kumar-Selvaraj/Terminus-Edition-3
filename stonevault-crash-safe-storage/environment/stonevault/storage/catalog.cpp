#include "catalog.hpp"

#include <algorithm>
#include <stdexcept>

namespace stonevault {

void VersionCatalog::load_snapshot(const SnapshotImage& image) {
    versions_.clear();
    for (const auto& row : image.rows) {
        versions_[row.key].push_back(Version{image.sequence, false, row.value});
    }
}

void VersionCatalog::apply_commit(const OrderedValues& writes, std::uint64_t sequence) {
    for (const auto& [key, value] : writes) {
        if (value.has_value()) {
            versions_[key].push_back(Version{sequence, false, *value});
        } else {
            versions_[key].push_back(Version{sequence, true, {}});
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
