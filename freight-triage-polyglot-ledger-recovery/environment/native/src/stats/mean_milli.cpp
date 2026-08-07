#include "freight/stats.h"

#include <algorithm>

namespace freight {

// mean_milli kernel.
long long stat_mean_milli(const std::vector<long long>& series) {
  if (series.empty()) {
    return 0;
  }
  long long total = 0;
  for (size_t i = 0; i < series.size(); ++i) {
    total += series[i];
  }
  return statFloorDiv(total * 1000, static_cast<long long>(series.size()));
}

}  // namespace freight
