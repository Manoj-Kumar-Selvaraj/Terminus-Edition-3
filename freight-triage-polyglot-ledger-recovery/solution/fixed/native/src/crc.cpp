#include "freight/crc.h"

#include <cstdio>

namespace freight {
namespace {

struct Crc32Table {
  uint32_t entries[256];
  Crc32Table() {
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t value = i;
      for (int bit = 0; bit < 8; ++bit) {
        value = (value & 1u) ? (0xEDB88320u ^ (value >> 1)) : (value >> 1);
      }
      entries[i] = value;
    }
  }
};

const Crc32Table& table() {
  static const Crc32Table instance;
  return instance;
}

}  // namespace

uint32_t crc32Ieee(const std::string& data) {
  const Crc32Table& lookup = table();
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    crc = lookup.entries[(crc ^ byte) & 0xFFu] ^ (crc >> 8);
  }
  return crc ^ 0xFFFFFFFFu;
}

std::string sealDigestHex(const std::string& normalizedSeal) {
  uint32_t value = crc32Ieee(normalizedSeal);
  char buffer[16];
  std::snprintf(buffer, sizeof(buffer), "%08x", value);
  return std::string(buffer);
}

}  // namespace freight
