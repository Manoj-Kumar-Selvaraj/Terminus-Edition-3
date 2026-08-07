#include "freight/hashes.h"

namespace freight {

// adler32 over raw bytes.
uint64_t hash_adler32(const std::string& data) {
  uint32_t low = 1u;
  uint32_t high = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    low = (low + static_cast<uint8_t>(data[i])) % 65521u;
    high = (high + low) % 65521u;
  }
  return static_cast<uint64_t>((high << 16) | low);
}

}  // namespace freight
