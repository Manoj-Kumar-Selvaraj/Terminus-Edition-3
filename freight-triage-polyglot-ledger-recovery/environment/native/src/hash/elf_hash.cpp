#include "freight/hashes.h"

namespace freight {

// elf_hash over raw bytes.
uint64_t hash_elf_hash(const std::string& data) {
  uint32_t state = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    state = (state << 4) + static_cast<uint8_t>(data[i]);
    uint32_t high = state & 0xF0000000u;
    if (high != 0u) {
      state ^= high >> 24;
    }
    state &= ~high;
  }
  return static_cast<uint64_t>(state);
}

}  // namespace freight
