#include "freight/codecs.h"

namespace freight {

// uleb128_tagged encoder.
std::string codec_encode_uleb128_tagged(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint32_t value = (static_cast<uint32_t>(static_cast<uint8_t>(data[i])) << 3) |
                     (static_cast<uint32_t>(static_cast<uint8_t>(data[i])) & 7u);
    while (value >= 0x80u) {
      out.push_back(static_cast<char>(static_cast<uint8_t>((value & 0x7Fu) | 0x80u)));
      value >>= 7;
    }
    out.push_back(static_cast<char>(static_cast<uint8_t>(value)));
  }
  return out;
}

// uleb128_tagged decoder; inverse of the encoder above.
std::string codec_decode_uleb128_tagged(const std::string& data) {
  std::string out;
  uint32_t value = 0;
  int shift = 0;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    value |= static_cast<uint32_t>(byte & 0x7Fu) << shift;
    if ((byte & 0x80u) != 0) {
      shift += 7;
      continue;
    }
    out.push_back(static_cast<char>(static_cast<uint8_t>(value >> 3)));
    value = 0;
    shift = 0;
  }
  return out;
}

}  // namespace freight
