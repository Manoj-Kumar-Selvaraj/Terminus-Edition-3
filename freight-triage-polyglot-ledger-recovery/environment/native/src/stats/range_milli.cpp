#include "freight/stats.h"

#include <algorithm>

namespace freight {

// range_milli kernel.
long long stat_range_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  long long low = series[0];
  long long high = series[0];
  for (size_t i = 1; i < series.size(); ++i) {
    if (series[i] < low) {
      low = series[i];
    }
    if (series[i] > high) {
      high = series[i];
    }
  }
  return (high - low) * 1000;
}

}  // namespace freight
