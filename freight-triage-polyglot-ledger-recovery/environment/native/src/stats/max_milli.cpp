#include "freight/stats.h"

#include <algorithm>

namespace freight {

// max_milli kernel.
long long stat_max_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  long long best = series[0];
  for (size_t i = 1; i < series.size(); ++i) {
    if (series[i] > best) {
      best = series[i];
    }
  }
  return best * 1000;
}

}  // namespace freight
