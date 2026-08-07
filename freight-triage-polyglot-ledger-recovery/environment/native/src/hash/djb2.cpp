#include "freight/hashes.h"

namespace freight {

// djb2 over raw bytes.
uint64_t hash_djb2(const std::string& data) {
  uint32_t state = 5381u;
  for (size_t i = 0; i < data.size(); ++i) {
    state = state * 33u + static_cast<uint8_t>(data[i]);
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
