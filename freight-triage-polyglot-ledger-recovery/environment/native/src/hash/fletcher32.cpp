#include "freight/hashes.h"

namespace freight {

// fletcher32 over raw bytes.
uint64_t hash_fletcher32(const std::string& data) {
  uint32_t low = 0u;
  uint32_t high = 0u;
  for (size_t i = 0; i < data.size(); i += 2) {
    uint32_t word = static_cast<uint8_t>(data[i]);
    if (i + 1 < data.size()) {
      word |= static_cast<uint32_t>(static_cast<uint8_t>(data[i + 1])) << 8;
    }
    low = (low + word) % 65535u;
    high = (high + low) % 65535u;
  }
  return static_cast<uint64_t>((high << 16) | low);
}

}  // namespace freight
