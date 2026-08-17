#pragma once

#include "common.hpp"

#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace stonevault {

struct CatalogAudit {
    std::size_t key_histories{};
    std::size_t total_versions{};
    std::size_t visible_keys{};
    std::size_t tombstone_versions{};
    std::size_t value_versions{};
    std::size_t multi_version_histories{};
    std::size_t tombstoned_histories{};
    std::size_t max_history_depth{};
    std::uint64_t max_sequence{};
};

class VersionCatalog {
public:
    void load_snapshot(const SnapshotImage& image);
    void apply_commit(const OrderedValues& writes, std::uint64_t sequence);

    std::optional<std::string> visible_value(const std::string& key, std::uint64_t snapshot) const;
    OrderedValues scan(const std::string& prefix, std::uint64_t snapshot) const;

    bool conflicts(const OrderedValues& writes, std::uint64_t snapshot) const;
    std::size_t visible_key_count(std::uint64_t snapshot) const;
    SnapshotImage snapshot_image(std::uint64_t sequence) const;
    std::uint64_t latest_sequence_for(const std::string& key) const;
    CatalogAudit audit(std::uint64_t committed_sequence) const;

private:
    std::map<std::string, std::vector<Version>, ByteLess> versions_;

    static std::optional<std::string> visible_from_versions(
        const std::vector<Version>& versions,
        std::uint64_t snapshot);
    static bool starts_with(const std::string& value, const std::string& prefix);
};

}  // namespace stonevault
