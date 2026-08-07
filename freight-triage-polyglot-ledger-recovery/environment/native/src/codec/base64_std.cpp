#include "freight/codecs.h"

namespace freight {

// base64_std encoder.
std::string codec_encode_base64_std(const std::string& data) {
  static const char kAlphabet[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string out;
  size_t index = 0;
  while (index < data.size()) {
    uint32_t buffer = 0;
    size_t take = data.size() - index;
    if (take > 3) {
      take = 3;
    }
    for (size_t i = 0; i < 3; ++i) {
      buffer <<= 8;
      if (i < take) {
        buffer |= static_cast<uint8_t>(data[index + i]);
      }
    }
    index += take;
    int emit = static_cast<int>(take) + 1;
    for (int i = 0; i < 4; ++i) {
      if (i < emit) {
        out.push_back(kAlphabet[(buffer >> (18 - 6 * i)) & 0x3Fu]);
      } else {
        out.push_back('=');
      }
    }
  }
  return out;
}

// base64_std decoder; inverse of the encoder above.
std::string codec_decode_base64_std(const std::string& data) {
  std::string out;
  uint32_t buffer = 0;
  int bits = 0;
  for (size_t i = 0; i < data.size(); ++i) {
    char c = data[i];
    if (c == '=') {
      continue;
    }
    int value = base64Value(c);
    if (value < 0) {
      return std::string();
    }
    buffer = (buffer << 6) | static_cast<uint32_t>(value);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out.push_back(static_cast<char>((buffer >> bits) & 0xFFu));
    }
  }
  return out;
}

}  // namespace freight
