#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: digits only.
std::string norm_digits_only(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size(); ++i) {
    if (text[i] >= '0' && text[i] <= '9') {
      out.push_back(text[i]);
    }
  }
  return out;
}

}  // namespace freight
