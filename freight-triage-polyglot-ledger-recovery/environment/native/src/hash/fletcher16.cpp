#include "freight/hashes.h"

namespace freight {

// fletcher16 over raw bytes.
uint64_t hash_fletcher16(const std::string& data) {
  uint32_t low = 0u;
  uint32_t high = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    low = (low + static_cast<uint8_t>(data[i])) % 255u;
    high = (high + low) % 255u;
  }
  return static_cast<uint64_t>((high << 8) | low);
}

}  // namespace freight
