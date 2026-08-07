#include "freight/hashes.h"

namespace freight {

// sdbm over raw bytes.
uint64_t hash_sdbm(const std::string& data) {
  uint32_t state = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    uint32_t byte = static_cast<uint8_t>(data[i]);
    state = byte + (state << 6) + (state << 16) - state;
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
