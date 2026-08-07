#include "freight/codecs.h"

namespace freight {

// xor_pad8 encoder.
std::string codec_encode_xor_pad8(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    out.push_back(static_cast<char>(static_cast<uint8_t>(data[i]) ^ kXorPad[i % 8]));
  }
  return out;
}

// xor_pad8 decoder; inverse of the encoder above.
std::string codec_decode_xor_pad8(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    out.push_back(static_cast<char>(static_cast<uint8_t>(data[i]) ^ kXorPad[i % 8]));
  }
  return out;
}

}  // namespace freight
