#include "freight/formats.h"

#include <algorithm>
#include <cstdio>

namespace freight {

// Formatter: thousands group.
std::string fmt_thousands_group(long long value) {
  bool negative = value < 0;
  long long absolute = negative ? -value : value;
  const std::string digits = std::to_string(absolute);
  std::string grouped;
  int count = 0;
  for (int i = static_cast<int>(digits.size()) - 1; i >= 0; --i) {
    grouped.push_back(digits[static_cast<size_t>(i)]);
    ++count;
    if (count % 3 == 0 && i > 0) {
      grouped.push_back(',');
    }
  }
  std::reverse(grouped.begin(), grouped.end());
  return negative ? "-" + grouped : grouped;
}

}  // namespace freight
