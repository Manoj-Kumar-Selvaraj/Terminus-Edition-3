#include "freight/hashes.h"

namespace freight {

// fnv1a64 over raw bytes.
uint64_t hash_fnv1a64(const std::string& data) {
  uint64_t state = 14695981039346656037ULL;
  for (size_t i = 0; i < data.size(); ++i) {
    state ^= static_cast<uint8_t>(data[i]);
    state *= 1099511628211ULL;
  }
  return state;
}

}  // namespace freight
