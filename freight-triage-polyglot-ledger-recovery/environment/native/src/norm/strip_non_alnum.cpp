#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: strip non alnum.
std::string norm_strip_non_alnum(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size(); ++i) {
    char c = text[i];
    if ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
      out.push_back(c);
    }
  }
  return out;
}

}  // namespace freight
