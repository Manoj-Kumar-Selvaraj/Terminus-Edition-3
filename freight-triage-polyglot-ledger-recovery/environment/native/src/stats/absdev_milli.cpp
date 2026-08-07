#include "freight/stats.h"

#include <algorithm>

namespace freight {

// absdev_milli kernel.
long long stat_absdev_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  long long count = static_cast<long long>(series.size());
  long long total = 0;
  for (size_t i = 0; i < series.size(); ++i) {
    total += series[i];
  }
  long long mean = statFloorDiv(total * 1000, count);
  long long accumulator = 0;
  for (size_t i = 0; i < series.size(); ++i) {
    long long delta = series[i] * 1000 - mean;
    accumulator += delta < 0 ? -delta : delta;
  }
  return statFloorDiv(accumulator, count);
}

}  // namespace freight
