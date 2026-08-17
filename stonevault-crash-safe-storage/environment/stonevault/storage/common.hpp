#pragma once

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace stonevault {

constexpr std::uint32_t kWalMagic = 0x31575653U;
constexpr std::size_t kWalHeaderSize = 12;
constexpr std::uint32_t kMaxWalPayload = 8U * 1024U * 1024U;
constexpr std::uint32_t kMaxKeyBytes = 4096U;
constexpr std::uint32_t kMaxValueBytes = 1024U * 1024U;
constexpr char kSnapshotMagic[8] = {'S','V','S','N','A','P','1','\0'};

struct ByteLess {
    bool operator()(const std::string& lhs, const std::string& rhs) const noexcept;
};

using OrderedValues = std::map<std::string, std::optional<std::string>, ByteLess>;

struct Version {
    std::uint64_t sequence{0};
    bool tombstone{false};
    std::string value;
};

struct Transaction {
    std::uint64_t id{0};
    std::uint64_t snapshot{0};
    OrderedValues writes;
};

struct SnapshotRow {
    std::string key;
    std::string value;
};

struct SnapshotImage {
    std::uint64_t sequence{0};
    std::vector<SnapshotRow> rows;
};

enum class WalRecordType : std::uint8_t {
    Put = 1,
    Delete = 2,
    Commit = 3,
};

struct WalMutation {
    WalRecordType type{WalRecordType::Put};
    std::uint64_t tx_id{0};
    std::string key;
    std::string value;
};

struct WalCommit {
    std::uint64_t tx_id{0};
    std::uint64_t sequence{0};
};

struct RecoveredCommit {
    std::uint64_t sequence{0};
    OrderedValues writes;
};

struct RecoveryResult {
    std::vector<RecoveredCommit> commits;
    std::uint64_t max_tx_id{0};
    bool truncated_torn_tail{false};
};

}  // namespace stonevault
