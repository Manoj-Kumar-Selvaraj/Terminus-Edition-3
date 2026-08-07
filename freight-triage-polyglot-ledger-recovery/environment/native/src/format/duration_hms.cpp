#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: duration hms.
std::string fmt_duration_hms(long long value) {
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%s%02lld:%02lld:%02lld", negative ? "-" : "",
                absolute / 3600, (absolute / 60) % 60, absolute % 60);
  return std::string(buffer);
}

}  // namespace freight
