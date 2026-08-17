#pragma once

#include "common.hpp"

#include <filesystem>

namespace stonevault {

class SnapshotStore {
public:
    SnapshotStore(std::filesystem::path directory, std::filesystem::path path);

    SnapshotImage load() const;
    void publish(const SnapshotImage& image) const;
    void remove_stale_temporary() const;

private:
    std::filesystem::path directory_;
    std::filesystem::path path_;
    std::filesystem::path temporary_path_;

    SnapshotRow parse_row(
        const std::vector<unsigned char>& bytes,
        std::size_t& pos,
        std::size_t row_index) const;
};

}  // namespace stonevault
