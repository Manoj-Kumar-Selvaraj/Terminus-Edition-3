#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: hex dump8.
std::string fmt_hex_dump8(long long value) {
  unsigned int truncated = static_cast<unsigned int>(static_cast<unsigned long long>(value) &
                                                    0xFFFFFFFFULL);
  char buffer[32];
  std::snprintf(buffer, sizeof(buffer), "%08x", truncated);
  return std::string(buffer);
}

}  // namespace freight
