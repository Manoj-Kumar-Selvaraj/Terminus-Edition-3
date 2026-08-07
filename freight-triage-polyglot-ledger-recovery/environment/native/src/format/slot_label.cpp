#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: slot label.
std::string fmt_slot_label(long long value) {
  if (value <= 0) {
    return "S--";
  }
  char buffer[32];
  std::snprintf(buffer, sizeof(buffer), "S%02lld", value % 100);
  return std::string(buffer);
}

}  // namespace freight
