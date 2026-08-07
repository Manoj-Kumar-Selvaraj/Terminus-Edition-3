#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: base36 upper.
std::string fmt_base36_upper(long long value) {
  static const char kDigits[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  if (value == 0) {
    return "0";
  }
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  std::string out;
  while (absolute > 0) {
    out.push_back(kDigits[absolute % 36]);
    absolute /= 36;
  }
  std::reverse(out.begin(), out.end());
  return negative ? "-" + out : out;
}

}  // namespace freight
