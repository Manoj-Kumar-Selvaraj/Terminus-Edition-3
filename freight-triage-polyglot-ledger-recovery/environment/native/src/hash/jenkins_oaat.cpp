#include "freight/hashes.h"

namespace freight {

// jenkins_oaat over raw bytes.
uint64_t hash_jenkins_oaat(const std::string& data) {
  uint32_t state = 0u;
  for (size_t i = 0; i < data.size(); ++i) {
    state += static_cast<uint8_t>(data[i]);
    state += state << 10;
    state ^= state >> 6;
  }
  state += state << 3;
  state ^= state >> 11;
  state += state << 15;
  return static_cast<uint64_t>(state);
}

}  // namespace freight
