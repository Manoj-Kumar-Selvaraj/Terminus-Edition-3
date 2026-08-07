#include "freight/stats.h"

#include <algorithm>

namespace freight {

// ewma_milli kernel.
long long stat_ewma_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  long long state = series[0] * 1000;
  for (size_t i = 1; i < series.size(); ++i) {
    state += statFloorDiv(series[i] * 1000 - state, 4);
  }
  return state;
}

}  // namespace freight
