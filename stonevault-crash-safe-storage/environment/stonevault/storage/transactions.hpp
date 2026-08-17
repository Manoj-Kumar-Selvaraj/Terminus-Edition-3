#pragma once

#include "common.hpp"

#include <cstddef>
#include <cstdint>
#include <map>
#include <string>

namespace stonevault {

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
