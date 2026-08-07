#include "freight/codecs.h"

namespace freight {

// delta_byte encoder.
std::string codec_encode_delta_byte(const std::string& data) {
  std::string out;
  uint8_t previous = 0;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t current = static_cast<uint8_t>(data[i]);
    out.push_back(static_cast<char>(static_cast<uint8_t>(current - previous)));
    previous = current;
  }
  return out;
}

// delta_byte decoder; inverse of the encoder above.
std::string codec_decode_delta_byte(const std::string& data) {
  std::string out;
  uint8_t previous = 0;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t current = static_cast<uint8_t>(static_cast<uint8_t>(data[i]) + previous);
    out.push_back(static_cast<char>(current));
    previous = current;
  }
  return out;
}

}  // namespace freight
