#include "freight/codecs.h"

namespace freight {

// escape_high encoder.
std::string codec_encode_escape_high(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    if (byte == 0x1Bu) {
      out.push_back(static_cast<char>(0x1B));
      out.push_back(static_cast<char>(0x7F));
    } else if (byte >= 0x80u) {
      out.push_back(static_cast<char>(0x1B));
      out.push_back(static_cast<char>(static_cast<uint8_t>(byte - 0x80u)));
    } else {
      out.push_back(static_cast<char>(byte));
    }
  }
  return out;
}

// escape_high decoder; inverse of the encoder above.
std::string codec_decode_escape_high(const std::string& data) {
  std::string out;
  for (size_t i = 0; i < data.size(); ++i) {
    uint8_t byte = static_cast<uint8_t>(data[i]);
    if (byte != 0x1Bu) {
      out.push_back(static_cast<char>(byte));
      continue;
    }
    if (i + 1 >= data.size()) {
      break;
    }
    uint8_t next = static_cast<uint8_t>(data[++i]);
    if (next == 0x7Fu) {
      out.push_back(static_cast<char>(0x1B));
    } else {
      out.push_back(static_cast<char>(static_cast<uint8_t>(next + 0x80u)));
    }
  }
  return out;
}

}  // namespace freight
