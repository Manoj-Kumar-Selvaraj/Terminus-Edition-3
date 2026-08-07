#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: lane label.
std::string fmt_lane_label(long long value) {
  long long index = ((value % 1000) + 1000) % 1000;
  char buffer[32];
  std::snprintf(buffer, sizeof(buffer), "LN-%03lld", index);
  return std::string(buffer);
}

}  // namespace freight
