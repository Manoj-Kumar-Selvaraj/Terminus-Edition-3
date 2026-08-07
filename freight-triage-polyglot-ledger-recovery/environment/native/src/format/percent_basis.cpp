#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: percent basis.
std::string fmt_percent_basis(long long value) {
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%s%lld.%02lld%%", negative ? "-" : "", absolute / 100,
                absolute % 100);
  return std::string(buffer);
}

}  // namespace freight
