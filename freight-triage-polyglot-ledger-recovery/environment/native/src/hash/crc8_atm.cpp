#include "freight/hashes.h"

namespace freight {

// crc8_atm over raw bytes.
uint64_t hash_crc8_atm(const std::string& data) {
  uint32_t crc = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    crc ^= static_cast<uint8_t>(data[i]);
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x80u) ? (((crc << 1) ^ 0x07u) & 0xFFu) : ((crc << 1) & 0xFFu);
    }
  }
  return static_cast<uint64_t>(crc & 0xFFu);
}

}  // namespace freight
