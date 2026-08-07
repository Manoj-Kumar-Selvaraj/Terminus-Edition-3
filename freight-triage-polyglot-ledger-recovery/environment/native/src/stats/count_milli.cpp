#include "freight/stats.h"

#include <algorithm>

namespace freight {

// count_milli kernel.
long long stat_count_milli(const std::vector<long long>& series) {
  return static_cast<long long>(series.size()) * 1000;
}

}  // namespace freight
