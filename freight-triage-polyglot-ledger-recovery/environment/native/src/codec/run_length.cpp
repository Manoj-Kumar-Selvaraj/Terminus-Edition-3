#include "freight/codecs.h"

namespace freight {

// run_length encoder.
std::string codec_encode_run_length(const std::string& data) {
  std::string out;
  size_t index = 0;
  while (index < data.size()) {
    char value = data[index];
    size_t run = 1;
    while (index + run < data.size() && data[index + run] == value && run < 255) {
      ++run;
    }
    out.push_back(static_cast<char>(static_cast<uint8_t>(run)));
    out.push_back(value);
    index += run;
  }
  return out;
}

// run_length decoder; inverse of the encoder above.
std::string codec_decode_run_length(const std::string& data) {
  std::string out;
  for (size_t i = 0; i + 1 < data.size(); i += 2) {
    size_t run = static_cast<uint8_t>(data[i]);
    for (size_t k = 0; k < run; ++k) {
      out.push_back(data[i + 1]);
    }
  }
  return out;
}

}  // namespace freight
