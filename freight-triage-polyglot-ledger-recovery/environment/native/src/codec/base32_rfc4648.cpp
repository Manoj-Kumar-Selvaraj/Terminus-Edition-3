#include "freight/codecs.h"

namespace freight {

// base32_rfc4648 encoder.
std::string codec_encode_base32_rfc4648(const std::string& data) {
  static const char kAlphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  std::string out;
  size_t index = 0;
  while (index < data.size()) {
    uint8_t group[5] = {0, 0, 0, 0, 0};
    size_t take = data.size() - index;
    if (take > 5) {
      take = 5;
    }
    for (size_t i = 0; i < take; ++i) {
      group[i] = static_cast<uint8_t>(data[index + i]);
    }
    index += take;
    uint64_t buffer = 0;
    for (int i = 0; i < 5; ++i) {
      buffer = (buffer << 8) | group[i];
    }
    static const int kChars[6] = {0, 2, 4, 5, 7, 8};
    int emit = kChars[take];
    for (int i = 0; i < 8; ++i) {
      if (i < emit) {
        out.push_back(kAlphabet[(buffer >> (35 - 5 * i)) & 0x1Fu]);
      } else {
        out.push_back('=');
      }
    }
  }
  return out;
}

// base32_rfc4648 decoder; inverse of the encoder above.
std::string codec_decode_base32_rfc4648(const std::string& data) {
  std::string out;
  uint64_t buffer = 0;
  int bits = 0;
  for (size_t i = 0; i < data.size(); ++i) {
    char c = data[i];
    if (c == '=') {
      continue;
    }
    int value = base32Value(c);
    if (value < 0) {
      return std::string();
    }
    buffer = (buffer << 5) | static_cast<uint64_t>(value);
    bits += 5;
    if (bits >= 8) {
      bits -= 8;
      out.push_back(static_cast<char>((buffer >> bits) & 0xFFu));
    }
  }
  return out;
}

}  // namespace freight
