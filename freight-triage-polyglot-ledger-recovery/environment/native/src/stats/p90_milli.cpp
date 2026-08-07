#include "freight/stats.h"

#include <algorithm>

namespace freight {

// p90_milli kernel.
long long stat_p90_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  std::vector<long long> sorted(series);
  std::sort(sorted.begin(), sorted.end());
  long long count = static_cast<long long>(sorted.size());
  long long rank = (9 * count + 9) / 10;
  if (rank < 1) {
    rank = 1;
  }
  if (rank > count) {
    rank = count;
  }
  return sorted[static_cast<size_t>(rank - 1)] * 1000;
}

}  // namespace freight
