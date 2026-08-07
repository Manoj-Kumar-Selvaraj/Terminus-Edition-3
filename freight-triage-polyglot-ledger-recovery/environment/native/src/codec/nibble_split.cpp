#include "freight/codecs.h"

namespace freight {

// nibble_split encoder.
std::string codec_encode_nibble_split(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    out.push_back(static_cast<char>('A' + (byte >> 4)));
    out.push_back(static_cast<char>('a' + (byte & 0x0Fu)));
  }
  return out;
}

// nibble_split decoder; inverse of the encoder above.
std::string codec_decode_nibble_split(const std::string& data) {
  std::string out;
  for (size_t i = 0; i + 1 < data.size(); i += 2) {
    uint8_t high = static_cast<uint8_t>(data[i] - 'A');
    uint8_t low = static_cast<uint8_t>(data[i + 1] - 'a');
    out.push_back(static_cast<char>(static_cast<uint8_t>((high << 4) | (low & 0x0Fu))));
  }
  return out;
}

}  // namespace freight
