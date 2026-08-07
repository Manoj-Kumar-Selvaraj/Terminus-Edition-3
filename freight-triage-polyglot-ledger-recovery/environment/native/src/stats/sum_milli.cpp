#include "freight/stats.h"

#include <algorithm>

namespace freight {

// sum_milli kernel.
long long stat_sum_milli(const std::vector<long long>& series) {
  long long total = 0;
  for (size_t i = 0; i < series.size(); ++i) {
    total += series[i];
  }
  return total * 1000;
}

}  // namespace freight
