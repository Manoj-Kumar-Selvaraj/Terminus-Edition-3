#pragma once

#include "common.hpp"

#include <cstddef>
#include <cstdint>
#include <map>
#include <string>

namespace stonevault {

struct TransactionAudit {
    std::size_t active_transactions{};
    std::size_t pending_mutations{};
    std::size_t pending_puts{};
    std::size_t pending_deletes{};
    std::size_t transactions_with_writes{};
    std::size_t max_write_set_size{};
    std::uint64_t oldest_snapshot{};
    std::uint64_t newest_snapshot{};
    std::uint64_t highest_transaction_id{};
};

class TransactionTable {
public:
    explicit TransactionTable(std::uint64_t next_id = 1);

    std::uint64_t begin(std::uint64_t snapshot);
    Transaction& require(std::uint64_t tx_id);
    const Transaction& require(std::uint64_t tx_id) const;

    bool contains(std::uint64_t tx_id) const;
    bool erase(std::uint64_t tx_id);
    bool empty() const noexcept;
    std::size_t size() const noexcept;

    std::uint64_t next_id() const noexcept;
    void advance_next_id(std::uint64_t minimum_next_id);
    TransactionAudit audit(std::uint64_t committed_sequence) const;

private:
    std::uint64_t next_id_;
    std::map<std::uint64_t, Transaction> active_;
};

OrderedValues apply_transaction_overlay(
    OrderedValues base,
    const OrderedValues& writes,
    const std::string& prefix);

bool key_has_prefix(
    const std::string& key,
    const std::string& prefix) noexcept;

}  // namespace stonevault
