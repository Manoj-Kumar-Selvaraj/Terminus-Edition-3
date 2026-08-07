#include "freight/hashes.h"

namespace freight {

// bsd_sum16 over raw bytes.
uint64_t hash_bsd_sum16(const std::string& data) {
  uint32_t state = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    state = ((state >> 1) | ((state & 1u) << 15)) & 0xFFFFu;
    state = (state + static_cast<uint8_t>(data[i])) & 0xFFFFu;
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
