#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: sign prefix.
std::string fmt_sign_prefix(long long value) {
  if (value == 0) {
    return "0";
  }
  if (value > 0) {
    return "+" + std::to_string(value);
  }
  return std::to_string(value);
}

}  // namespace freight
