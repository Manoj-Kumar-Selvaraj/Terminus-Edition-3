#pragma once

#include "common.hpp"

#include <cstdint>
#include <filesystem>
#include <map>
#include <string>
#include <vector>

namespace stonevault {

class WalManager {
public:
    explicit WalManager(std::filesystem::path path);
    WalManager(const WalManager&) = delete;
    WalManager& operator=(const WalManager&) = delete;
    ~WalManager();

    void append_put(std::uint64_t tx_id, const std::string& key, const std::string& value);
    void append_delete(std::uint64_t tx_id, const std::string& key);
    void append_commit(std::uint64_t tx_id, std::uint64_t sequence);
    void sync_commit();

    RecoveryResult recover(std::uint64_t snapshot_sequence);
    void reset_after_checkpoint();
    std::uint64_t size() const;

private:
    std::filesystem::path path_;
    int fd_{-1};

    void append_record(const std::vector<unsigned char>& payload);
    void truncate_to(std::size_t valid_end);
    WalMutation parse_mutation(const std::vector<unsigned char>& payload) const;
    WalCommit parse_commit(const std::vector<unsigned char>& payload) const;
};

}  // namespace stonevault
