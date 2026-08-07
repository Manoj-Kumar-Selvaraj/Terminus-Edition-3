#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: reverse bytes.
std::string norm_reverse_bytes(const std::string& text) {
  std::string out(text);
  std::reverse(out.begin(), out.end());
  return out;
}

}  // namespace freight
