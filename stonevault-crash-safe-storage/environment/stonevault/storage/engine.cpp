#include "engine.hpp"

#include "catalog.hpp"
#include "codec.hpp"
#include "common.hpp"
#include "lock.hpp"
#include "integrity.hpp"
#include "maintenance.hpp"
#include "recovery.hpp"
#include "transactions.hpp"
#include "snapshot.hpp"
#include "wal.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

namespace stonevault {

namespace {

char* duplicate_string(const std::string& value) {
    char* output = static_cast<char*>(std::malloc(value.size() + 1));
    if (output == nullptr) {
        return nullptr;
    }
    std::memcpy(output, value.data(), value.size());
    output[value.size()] = '\0';
    return output;
}

void set_error(char* err, std::size_t err_len, const std::string& message) {
    if (err == nullptr || err_len == 0) {
        return;
    }
    const std::size_t length = std::min(err_len - 1, message.size());
    std::memcpy(err, message.data(), length);
    err[length] = '\0';
}

std::string require_hex(const char* text, const char* field) {
    auto decoded = codec::hex_decode(text);
    if (!decoded.has_value()) {
        throw std::runtime_error(
            std::string(field) + " must be even-length hexadecimal");
    }
    return *decoded;
}

void validate_key(const std::string& key) {
    if (key.size() > kMaxKeyBytes) {
        throw std::runtime_error("key exceeds 4096 bytes");
    }
}

void validate_value(const std::string& value) {
    if (value.size() > kMaxValueBytes) {
        throw std::runtime_error("value exceeds 1048576 bytes");
    }
}

class Engine {
public:
    explicit Engine(const std::filesystem::path& directory)
        : paths_(prepare_storage_paths(directory)),
          writer_lock_(paths_.lock),
          snapshot_store_(paths_.directory, paths_.snapshot),
          wal_(paths_.wal) {
        const RecoveredDatabase recovered =
            restore_database(snapshot_store_, wal_, catalog_);
        commit_sequence_ = recovered.commit_sequence;
        transactions_.advance_next_id(recovered.next_transaction_id);
    }

    std::uint64_t current_sequence() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return commit_sequence_;
    }

    std::uint64_t begin() {
        std::lock_guard<std::mutex> guard(mutex_);
        return transactions_.begin(commit_sequence_);
    }

    void put(
        std::uint64_t tx_id,
        const std::string& key,
        const std::string& value) {
        validate_key(key);
        validate_value(value);

        std::lock_guard<std::mutex> guard(mutex_);
        Transaction& tx = transactions_.require(tx_id);
        wal_.append_put(tx_id, key, value);
        tx.writes[key] = value;
    }

    void erase(
        std::uint64_t tx_id,
        const std::string& key) {
        validate_key(key);

        std::lock_guard<std::mutex> guard(mutex_);
        Transaction& tx = transactions_.require(tx_id);
        wal_.append_delete(tx_id, key);
        tx.writes[key] = std::nullopt;
    }

    std::optional<std::string> get(
        std::uint64_t tx_id,
        const std::string& key) {
        validate_key(key);

        std::lock_guard<std::mutex> guard(mutex_);
        const Transaction& tx = transactions_.require(tx_id);
        const auto local = tx.writes.find(key);
        if (local != tx.writes.end()) {
            return local->second;
        }
        return catalog_.visible_value(key, commit_sequence_);
    }

    OrderedValues scan(
        std::uint64_t tx_id,
        const std::string& prefix) {
        validate_key(prefix);

        std::lock_guard<std::mutex> guard(mutex_);
        const Transaction& tx = transactions_.require(tx_id);
        return catalog_.scan(prefix, commit_sequence_);
    }

    int commit(
        std::uint64_t tx_id,
        std::uint64_t& sequence) {
        std::lock_guard<std::mutex> guard(mutex_);
        Transaction& tx = transactions_.require(tx_id);

        const std::uint64_t next_sequence = commit_sequence_ + 1;
        wal_.append_commit(tx_id, next_sequence);
        wal_.sync_commit();

        catalog_.apply_commit(tx.writes, next_sequence);
        commit_sequence_ = next_sequence;
        sequence = commit_sequence_;
        transactions_.erase(tx_id);
        return 0;
    }

    void rollback(std::uint64_t tx_id) {
        std::lock_guard<std::mutex> guard(mutex_);
        if (!transactions_.erase(tx_id)) {
            throw std::runtime_error("unknown transaction");
        }
    }

    int checkpoint(std::uint64_t& sequence) {
        std::lock_guard<std::mutex> guard(mutex_);
        SnapshotImage image =
            catalog_.snapshot_image(commit_sequence_);
        image.sequence = 0;
        snapshot_store_.publish(image);
        wal_.reset_after_checkpoint();
        sequence = commit_sequence_;
        return 0;
    }

    std::string stats() {
        std::lock_guard<std::mutex> guard(mutex_);
        const RuntimeAudit audit = audit_runtime_state(
            paths_, catalog_, transactions_, commit_sequence_);
        if (audit.storage.wal_bytes != wal_.size()) {
            throw std::runtime_error("runtime integrity: WAL size views disagree");
        }
        return render_stats(
            commit_sequence_,
            static_cast<std::uint64_t>(audit.catalog.visible_keys),
            audit.storage.wal_bytes);
    }

    std::string health() {
        std::lock_guard<std::mutex> guard(mutex_);
        return render_health(IntegrityReport{
            commit_sequence_,
            static_cast<std::uint64_t>(catalog_.visible_key_count(commit_sequence_)),
            0,
            wal_.size(),
            false,
        });
    }

private:
    StoragePaths paths_;
    WriterLock writer_lock_;
    SnapshotStore snapshot_store_;
    WalManager wal_;
    VersionCatalog catalog_;
    std::uint64_t commit_sequence_{0};
    TransactionTable transactions_;
    mutable std::mutex mutex_;
};

Engine* as_engine(void* handle) {
    if (handle == nullptr) {
        throw std::runtime_error("engine is not open");
    }
    return static_cast<Engine*>(handle);
}

}  // namespace

}  // namespace stonevault

extern "C" {

void* sv_open(
    const char* data_dir,
    char* err,
    std::size_t err_len) {
    try {
        if (data_dir == nullptr || *data_dir == '\0') {
            throw std::runtime_error("data directory is required");
        }
        return new stonevault::Engine(data_dir);
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return nullptr;
    }
}

void sv_close(void* handle) {
    delete static_cast<stonevault::Engine*>(handle);
}

std::uint64_t sv_current_sequence(void* handle) {
    try {
        return stonevault::as_engine(handle)->current_sequence();
    } catch (...) {
        return 0;
    }
}

std::uint64_t sv_begin(
    void* handle,
    char* err,
    std::size_t err_len) {
    try {
        return stonevault::as_engine(handle)->begin();
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return 0;
    }
}

int sv_put(
    void* handle,
    std::uint64_t tx_id,
    const char* key_hex,
    const char* value_hex,
    char* err,
    std::size_t err_len) {
    try {
        stonevault::as_engine(handle)->put(
            tx_id,
            stonevault::require_hex(key_hex, "key"),
            stonevault::require_hex(value_hex, "value"));
        return 0;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return -1;
    }
}

int sv_del(
    void* handle,
    std::uint64_t tx_id,
    const char* key_hex,
    char* err,
    std::size_t err_len) {
    try {
        stonevault::as_engine(handle)->erase(
            tx_id,
            stonevault::require_hex(key_hex, "key"));
        return 0;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return -1;
    }
}

char* sv_get(
    void* handle,
    std::uint64_t tx_id,
    const char* key_hex,
    int* status,
    char* err,
    std::size_t err_len) {
    try {
        auto value = stonevault::as_engine(handle)->get(
            tx_id,
            stonevault::require_hex(key_hex, "key"));
        if (!value.has_value()) {
            if (status != nullptr) {
                *status = 0;
            }
            return nullptr;
        }
        char* output =
            stonevault::duplicate_string(stonevault::codec::hex_encode(*value));
        if (output == nullptr) {
            throw std::runtime_error("out of memory");
        }
        if (status != nullptr) {
            *status = 1;
        }
        return output;
    } catch (const std::exception& error) {
        if (status != nullptr) {
            *status = -1;
        }
        stonevault::set_error(err, err_len, error.what());
        return nullptr;
    }
}

char* sv_scan(
    void* handle,
    std::uint64_t tx_id,
    const char* prefix_hex,
    int* status,
    char* err,
    std::size_t err_len) {
    try {
        const auto rows = stonevault::as_engine(handle)->scan(
            tx_id,
            stonevault::require_hex(prefix_hex, "prefix"));
        std::string encoded;
        bool first = true;
        for (const auto& [key, value] : rows) {
            if (!value.has_value()) {
                continue;
            }
            if (!first) {
                encoded.push_back(',');
            }
            first = false;
            encoded += stonevault::codec::hex_encode(key);
            encoded.push_back('=');
            encoded += stonevault::codec::hex_encode(*value);
        }
        char* output = stonevault::duplicate_string(encoded);
        if (output == nullptr) {
            throw std::runtime_error("out of memory");
        }
        if (status != nullptr) {
            *status = 0;
        }
        return output;
    } catch (const std::exception& error) {
        if (status != nullptr) {
            *status = -1;
        }
        stonevault::set_error(err, err_len, error.what());
        return nullptr;
    }
}

int sv_commit(
    void* handle,
    std::uint64_t tx_id,
    std::uint64_t* commit_seq,
    char* err,
    std::size_t err_len) {
    try {
        std::uint64_t sequence = 0;
        const int result =
            stonevault::as_engine(handle)->commit(tx_id, sequence);
        if (commit_seq != nullptr) {
            *commit_seq = sequence;
        }
        return result;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return -1;
    }
}

int sv_rollback(
    void* handle,
    std::uint64_t tx_id,
    char* err,
    std::size_t err_len) {
    try {
        stonevault::as_engine(handle)->rollback(tx_id);
        return 0;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return -1;
    }
}

int sv_checkpoint(
    void* handle,
    std::uint64_t* checkpoint_seq,
    char* err,
    std::size_t err_len) {
    try {
        std::uint64_t sequence = 0;
        const int result =
            stonevault::as_engine(handle)->checkpoint(sequence);
        if (checkpoint_seq != nullptr) {
            *checkpoint_seq = sequence;
        }
        return result;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return -1;
    }
}

char* sv_stats(
    void* handle,
    char* err,
    std::size_t err_len) {
    try {
        char* output = stonevault::duplicate_string(
            stonevault::as_engine(handle)->stats());
        if (output == nullptr) {
            throw std::runtime_error("out of memory");
        }
        return output;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return nullptr;
    }
}

char* sv_health(
    void* handle,
    char* err,
    std::size_t err_len) {
    try {
        char* output = stonevault::duplicate_string(
            stonevault::as_engine(handle)->health());
        if (output == nullptr) {
            throw std::runtime_error("out of memory");
        }
        return output;
    } catch (const std::exception& error) {
        stonevault::set_error(err, err_len, error.what());
        return nullptr;
    }
}

void sv_free_string(char* value) {
    std::free(value);
}

}
