#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: dash to underscore.
std::string norm_dash_to_underscore(const std::string& text) {
  std::string out(text);
  for (size_t i = 0; i < out.size(); ++i) {
    if (out[i] == '-') {
      out[i] = '_';
    }
  }
  return out;
}

}  // namespace freight
