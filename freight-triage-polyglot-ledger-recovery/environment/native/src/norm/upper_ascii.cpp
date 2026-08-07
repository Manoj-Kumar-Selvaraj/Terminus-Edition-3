#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: upper ascii.
std::string norm_upper_ascii(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size(); ++i) {
    char c = text[i];
    out.push_back((c >= 'a' && c <= 'z') ? static_cast<char>(c - 32) : c);
  }
  return out;
}

}  // namespace freight
