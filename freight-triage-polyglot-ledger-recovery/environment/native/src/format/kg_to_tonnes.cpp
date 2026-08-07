#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: kg to tonnes.
std::string fmt_kg_to_tonnes(long long value) {
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%s%lld.%03lld", negative ? "-" : "", absolute / 1000,
                absolute % 1000);
  return std::string(buffer);
}

}  // namespace freight
