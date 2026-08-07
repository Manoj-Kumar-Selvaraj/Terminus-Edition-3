#include "freight/codecs.h"

namespace freight {

// quoted_freight encoder.
std::string codec_encode_quoted_freight(const std::string& data) {
  static const char kDigits[] = "0123456789ABCDEF";
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    if (byte >= 0x20u && byte <= 0x7Eu && byte != '=') {
      out.push_back(static_cast<char>(byte));
      continue;
    }
    out.push_back('=');
    out.push_back(kDigits[byte >> 4]);
    out.push_back(kDigits[byte & 0x0Fu]);
  }
  return out;
}

// quoted_freight decoder; inverse of the encoder above.
std::string codec_decode_quoted_freight(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    if (data[i] != '=') {
      out.push_back(data[i]);
      continue;
    }
    if (i + 2 >= data.size()) {
      break;
    }
    int high = hexValue(data[i + 1]);
    int low = hexValue(data[i + 2]);
    if (high < 0 || low < 0) {
      return std::string();
    }
    out.push_back(static_cast<char>((high << 4) | low));
    i += 2;
  }
  return out;
}

}  // namespace freight
