#include "freight/codecs.h"

namespace freight {

// chunk16_framed encoder.
std::string codec_encode_chunk16_framed(const std::string& data) {
  std::string out;
  size_t index = 0;
  while (index < data.size()) {
    size_t take = data.size() - index;
    if (take > 16) {
      take = 16;
    }
    out.push_back(static_cast<char>(static_cast<uint8_t>(take)));
    out.append(data, index, take);
    index += take;
  }
  return out;
}

// chunk16_framed decoder; inverse of the encoder above.
std::string codec_decode_chunk16_framed(const std::string& data) {
  std::string out;
  size_t index = 0;
  while (index < data.size()) {
    size_t take = static_cast<uint8_t>(data[index]);
    ++index;
    if (index + take > data.size()) {
      take = data.size() - index;
    }
    out.append(data, index, take);
    index += take;
  }
  return out;
}

}  // namespace freight
