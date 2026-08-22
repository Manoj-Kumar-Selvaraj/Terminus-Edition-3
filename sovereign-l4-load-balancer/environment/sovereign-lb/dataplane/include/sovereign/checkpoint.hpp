#pragma once
#include "sovereign/snapshot.hpp"
#include <filesystem>
#include <optional>
namespace sovereign {
struct Checkpoint { std::shared_ptr<const Snapshot> snapshot; std::string canonical; std::string digest; };
class CheckpointStore { public: explicit CheckpointStore(std::filesystem::path root):root_(std::move(root)){} void save(const std::string& canonical,const std::string& digest,std::uint64_t generation); std::optional<Checkpoint> load_current() const; private: std::filesystem::path root_; std::optional<Checkpoint> load(std::uint64_t generation) const; };
}