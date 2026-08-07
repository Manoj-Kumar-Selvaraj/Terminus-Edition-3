#include "freight/hashes.h"

namespace freight {

// xor_rotate over raw bytes.
uint64_t hash_xor_rotate(const std::string& data) {
  uint32_t state = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    state = ((state << 5) | (state >> 27)) ^ static_cast<uint8_t>(data[i]);
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
