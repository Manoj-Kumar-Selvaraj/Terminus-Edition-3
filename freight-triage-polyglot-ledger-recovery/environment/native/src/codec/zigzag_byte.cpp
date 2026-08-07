#include "freight/codecs.h"

namespace freight {

// zigzag_byte encoder.
std::string codec_encode_zigzag_byte(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    int8_t value = static_cast<int8_t>(data[i]);
    uint8_t encoded = static_cast<uint8_t>((value << 1) ^ (value >> 7));
    out.push_back(static_cast<char>(encoded));
  }
  return out;
}

// zigzag_byte decoder; inverse of the encoder above.
std::string codec_decode_zigzag_byte(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t encoded = static_cast<uint8_t>(data[i]);
    int8_t value = static_cast<int8_t>((encoded >> 1) ^ (~(encoded & 1u) + 1u));
    out.push_back(static_cast<char>(value));
  }
  return out;
}

}  // namespace freight
