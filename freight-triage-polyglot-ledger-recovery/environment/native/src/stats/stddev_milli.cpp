#include "freight/stats.h"

#include <algorithm>

namespace freight {

// stddev_milli kernel.
long long stat_stddev_milli(const std::vector<long long>& series) {
  long long variance = stat_variance_milli(series);
  return statIntegerSqrt(variance * 1000);
}

}  // namespace freight
