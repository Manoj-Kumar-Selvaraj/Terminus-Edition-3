#include "freight/hashes.h"

namespace freight {

// crc32c over raw bytes.
uint64_t hash_crc32c(const std::string& data) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < data.size(); ++i) {
    crc ^= static_cast<uint8_t>(data[i]);
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc & 1u) ? ((crc >> 1) ^ 0x82F63B78u) : (crc >> 1);
    }
  }
  return static_cast<uint64_t>(crc ^ 0xFFFFFFFFu);
}

}  // namespace freight
