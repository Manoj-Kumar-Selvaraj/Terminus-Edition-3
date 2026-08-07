#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: collapse spaces.
std::string norm_collapse_spaces(const std::string& text) {
  std::string out;
  bool pending = false;
  for (size_t i = 0; i < text.size(); ++i) {
    if (text[i] == ' ') {
      pending = true;
      continue;
    }
    if (pending && !out.empty()) {
      out.push_back(' ');
    }
    pending = false;
    out.push_back(text[i]);
  }
  return out;
}

}  // namespace freight
