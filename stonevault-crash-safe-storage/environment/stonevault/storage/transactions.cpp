#include "transactions.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <utility>

namespace stonevault {

TransactionTable::TransactionTable(std::uint64_t next_id)
    : next_id_(next_id == 0 ? 1 : next_id) {}

std::uint64_t TransactionTable::begin(std::uint64_t snapshot) {
    if (next_id_ == std::numeric_limits<std::uint64_t>::max()) {
        throw std::runtime_error("transaction id space exhausted");
    }
    const std::uint64_t id = next_id_++;
    const auto [_, inserted] = active_.emplace(
        id,
        Transaction{
            id,
            snapshot,
            OrderedValues{},
        });
    if (!inserted) {
        throw std::runtime_error("transaction id collision");
    }
    return id;
}

Transaction& TransactionTable::require(std::uint64_t tx_id) {
    const auto found = active_.find(tx_id);
    if (found == active_.end()) {
        throw std::runtime_error("unknown transaction");
    }
    return found->second;
}

const Transaction& TransactionTable::require(std::uint64_t tx_id) const {
    const auto found = active_.find(tx_id);
    if (found == active_.end()) {
        throw std::runtime_error("unknown transaction");
    }
    return found->second;
}

bool TransactionTable::contains(std::uint64_t tx_id) const {
    return active_.find(tx_id) != active_.end();
}

bool TransactionTable::erase(std::uint64_t tx_id) {
    return active_.erase(tx_id) != 0;
}

bool TransactionTable::empty() const noexcept {
    return active_.empty();
}

std::size_t TransactionTable::size() const noexcept {
    return active_.size();
}

std::uint64_t TransactionTable::next_id() const noexcept {
    return next_id_;
}

void TransactionTable::advance_next_id(std::uint64_t minimum_next_id) {
    if (minimum_next_id == 0) {
        minimum_next_id = 1;
    }
    next_id_ = std::max(next_id_, minimum_next_id);
}

TransactionAudit TransactionTable::audit(std::uint64_t committed_sequence) const {
    TransactionAudit audit;
    bool first = true;

    if (next_id_ == 0) {
        throw std::runtime_error("transaction integrity: next id is zero");
    }

    for (const auto& [id, transaction] : active_) {
        if (id == 0 || transaction.id == 0 || id != transaction.id) {
            throw std::runtime_error("transaction integrity: active id mismatch");
        }
        if (id >= next_id_) {
            throw std::runtime_error("transaction integrity: active id is not below next id");
        }
        if (transaction.snapshot > committed_sequence) {
            throw std::runtime_error("transaction integrity: snapshot is newer than committed state");
        }

        ++audit.active_transactions;
        audit.highest_transaction_id = std::max(audit.highest_transaction_id, id);
        if (first || transaction.snapshot < audit.oldest_snapshot) {
            audit.oldest_snapshot = transaction.snapshot;
        }
        if (first || transaction.snapshot > audit.newest_snapshot) {
            audit.newest_snapshot = transaction.snapshot;
        }
        first = false;

        audit.max_write_set_size = std::max(audit.max_write_set_size, transaction.writes.size());
        if (!transaction.writes.empty()) {
            ++audit.transactions_with_writes;
        }
        for (const auto& [key, value] : transaction.writes) {
            if (key.size() > kMaxKeyBytes) {
                throw std::runtime_error("transaction integrity: pending key exceeds configured limit");
            }
            ++audit.pending_mutations;
            if (value.has_value()) {
                if (value->size() > kMaxValueBytes) {
                    throw std::runtime_error("transaction integrity: pending value exceeds configured limit");
                }
                ++audit.pending_puts;
            } else {
                ++audit.pending_deletes;
            }
        }
    }

    if (audit.pending_puts + audit.pending_deletes != audit.pending_mutations) {
        throw std::runtime_error("transaction integrity: mutation accounting mismatch");
    }
    if (audit.transactions_with_writes > audit.active_transactions) {
        throw std::runtime_error("transaction integrity: write-set accounting mismatch");
    }
    if (audit.max_write_set_size > audit.pending_mutations && audit.pending_mutations != 0) {
        throw std::runtime_error("transaction integrity: invalid maximum write-set size");
    }
    if (audit.active_transactions != active_.size()) {
        throw std::runtime_error("transaction integrity: active transaction accounting mismatch");
    }
    return audit;
}

bool key_has_prefix(
    const std::string& key,
    const std::string& prefix) noexcept {
    if (key.size() < prefix.size()) {
        return false;
    }
    return std::equal(prefix.begin(), prefix.end(), key.begin());
}

OrderedValues apply_transaction_overlay(
    OrderedValues base,
    const OrderedValues& writes,
    const std::string& prefix) {
    for (const auto& [key, value] : writes) {
        if (!key_has_prefix(key, prefix)) {
            continue;
        }
        if (value.has_value()) {
            base[key] = value;
        } else {
            base.erase(key);
        }
    }
    return base;
}

}  // namespace stonevault
