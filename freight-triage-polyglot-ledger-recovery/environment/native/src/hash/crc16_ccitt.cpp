#include "freight/hashes.h"

namespace freight {

// crc16_ccitt over raw bytes.
uint64_t hash_crc16_ccitt(const std::string& data) {
  uint32_t crc = 0xFFFFu;
  for (size_t i = 0; i < data.size(); ++i) {
    crc ^= static_cast<uint32_t>(static_cast<uint8_t>(data[i])) << 8;
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000u) ? (((crc << 1) ^ 0x1021u) & 0xFFFFu) : ((crc << 1) & 0xFFFFu);
    }
  }
  return static_cast<uint64_t>(crc & 0xFFFFu);
}

}  // namespace freight
