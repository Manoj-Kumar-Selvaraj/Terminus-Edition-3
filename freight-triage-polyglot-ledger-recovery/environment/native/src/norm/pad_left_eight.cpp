#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: pad left eight.
std::string norm_pad_left_eight(const std::string& text) {
  if (text.size() >= 8) {
    return text;
  }
  return std::string(8 - text.size(), '0') + text;
}

}  // namespace freight
