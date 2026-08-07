#include "freight/stats.h"

namespace freight {

long long statFloorDiv(long long numerator, long long denominator) {
  if (denominator == 0) {
    return 0;
  }
  long long quotient = numerator / denominator;
  long long remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) != (denominator < 0))) {
    quotient -= 1;
  }
  return quotient;
}

long long statIntegerSqrt(long long value) {
  if (value <= 0) {
    return 0;
  }
  long long low = 0;
  long long high = value < 3037000499LL ? value : 3037000499LL;
  while (low < high) {
    long long mid = low + (high - low + 1) / 2;
    if (mid <= value / mid) {
      low = mid;
    } else {
      high = mid - 1;
    }
  }
  return low;
}

}  // namespace freight
