#include "freight/normalize.h"

#include <algorithm>

namespace freight {

// Normalizer: rot13 letters.
std::string norm_rot13_letters(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size(); ++i) {
    char c = text[i];
    if (c >= 'a' && c <= 'z') {
      c = static_cast<char>('a' + (c - 'a' + 13) % 26);
    } else if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>('A' + (c - 'A' + 13) % 26);
    }
    out.push_back(c);
  }
  return out;
}

}  // namespace freight
