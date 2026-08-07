#include "freight/stats.h"

#include <algorithm>

namespace freight {

// median_milli kernel.
long long stat_median_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  std::vector<long long> sorted(series);
  std::sort(sorted.begin(), sorted.end());
  size_t middle = sorted.size() / 2;
  if (sorted.size() % 2 == 1) {
    return sorted[middle] * 1000;
  }
  return statFloorDiv((sorted[middle - 1] + sorted[middle]) * 1000, 2);
}

}  // namespace freight
