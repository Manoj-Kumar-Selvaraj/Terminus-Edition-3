#pragma once

#include "common.hpp"

#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace stonevault {

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

private:
    std::map<std::string, std::vector<Version>, ByteLess> versions_;

    static std::optional<std::string> visible_from_versions(
        const std::vector<Version>& versions,
        std::uint64_t snapshot);
    static bool starts_with(const std::string& value, const std::string& prefix);
};

}  // namespace stonevault
