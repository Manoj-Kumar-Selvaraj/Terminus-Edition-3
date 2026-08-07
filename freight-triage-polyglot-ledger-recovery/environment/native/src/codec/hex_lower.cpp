#include "freight/codecs.h"

namespace freight {

// hex_lower encoder.
std::string codec_encode_hex_lower(const std::string& data) {
  static const char kDigits[] = "0123456789abcdef";
  std::string out;
  out.reserve(data.size() * 2);
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    out.push_back(kDigits[byte >> 4]);
    out.push_back(kDigits[byte & 0x0Fu]);
  }
  return out;
}

// hex_lower decoder; inverse of the encoder above.
std::string codec_decode_hex_lower(const std::string& data) {
  std::string out;
  for (size_t i = 0; i + 1 < data.size(); i += 2) {
    int high = hexValue(data[i]);
    int low = hexValue(data[i + 1]);
    if (high < 0 || low < 0) {
      return std::string();
    }
    out.push_back(static_cast<char>((high << 4) | low));
  }
  return out;
}

}  // namespace freight
