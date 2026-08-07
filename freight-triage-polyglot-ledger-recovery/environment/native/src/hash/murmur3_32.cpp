#include "freight/hashes.h"

namespace freight {

// murmur3_32 over raw bytes.
uint64_t hash_murmur3_32(const std::string& data) {
  uint32_t state = 0x5F3A1C7Du;
  const size_t blocks = data.size() / 4;
  for (size_t i = 0; i < blocks; ++i) {
    uint32_t k = static_cast<uint32_t>(static_cast<uint8_t>(data[i * 4])) |
                 (static_cast<uint32_t>(static_cast<uint8_t>(data[i * 4 + 1])) << 8) |
                 (static_cast<uint32_t>(static_cast<uint8_t>(data[i * 4 + 2])) << 16) |
                 (static_cast<uint32_t>(static_cast<uint8_t>(data[i * 4 + 3])) << 24);
    k *= 0xCC9E2D51u;
    k = (k << 15) | (k >> 17);
    k *= 0x1B873593u;
    state ^= k;
    state = (state << 13) | (state >> 19);
    state = state * 5u + 0xE6546B64u;
  }
  uint32_t tail = 0u;
  const size_t remainder = data.size() & 3u;
  if (remainder >= 3) {
    tail ^= static_cast<uint32_t>(static_cast<uint8_t>(data[blocks * 4 + 2])) << 16;
  }
  if (remainder >= 2) {
    tail ^= static_cast<uint32_t>(static_cast<uint8_t>(data[blocks * 4 + 1])) << 8;
  }
  if (remainder >= 1) {
    tail ^= static_cast<uint32_t>(static_cast<uint8_t>(data[blocks * 4]));
    tail *= 0xCC9E2D51u;
    tail = (tail << 15) | (tail >> 17);
    tail *= 0x1B873593u;
    state ^= tail;
  }
  state ^= static_cast<uint32_t>(data.size());
  state ^= state >> 16;
  state *= 0x85EBCA6Bu;
  state ^= state >> 13;
  state *= 0xC2B2AE35u;
  state ^= state >> 16;
  return static_cast<uint64_t>(state);
}

}  // namespace freight
