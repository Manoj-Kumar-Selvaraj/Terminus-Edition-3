#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: ordinal suffix.
std::string fmt_ordinal_suffix(long long value) {
  long long mod100 = ((value % 100) + 100) % 100;
  long long mod10 = mod100 % 10;
  const char* suffix = "th";
  if (mod100 < 11 || mod100 > 13) {
    if (mod10 == 1) {
      suffix = "st";
    } else if (mod10 == 2) {
      suffix = "nd";
    } else if (mod10 == 3) {
      suffix = "rd";
    }
  }
  return std::to_string(value) + suffix;
}

}  // namespace freight
