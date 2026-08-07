#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: cents to amount.
std::string fmt_cents_to_amount(long long value) {
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%s%lld.%02lld", negative ? "-" : "", absolute / 100,
                absolute % 100);
  return std::string(buffer);
}

}  // namespace freight
