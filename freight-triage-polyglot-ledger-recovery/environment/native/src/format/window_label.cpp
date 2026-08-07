#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: window label.
std::string fmt_window_label(long long value) {
  long long index = ((value % 1000000) + 1000000) % 1000000;
  char buffer[32];
  std::snprintf(buffer, sizeof(buffer), "W-%06lld", index);
  return std::string(buffer);
}

}  // namespace freight
