#include "freight/hashes.h"

namespace freight {

// fnv1a32 over raw bytes.
uint64_t hash_fnv1a32(const std::string& data) {
  uint32_t state = 2166136261u;
  for (size_t i = 0; i < data.size(); ++i) {
    state ^= static_cast<uint8_t>(data[i]);
    state *= 16777619u;
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
