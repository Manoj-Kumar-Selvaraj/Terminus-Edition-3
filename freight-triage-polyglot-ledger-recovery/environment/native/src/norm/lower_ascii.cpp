#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: lower ascii.
std::string norm_lower_ascii(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size(); ++i) {
    char c = text[i];
    out.push_back((c >= 'A' && c <= 'Z') ? static_cast<char>(c + 32) : c);
  }
  return out;
}

}  // namespace freight
