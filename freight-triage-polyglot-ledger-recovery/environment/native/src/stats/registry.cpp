#include "freight/stats.h"

namespace freight {

const std::vector<StatKernel>& statRegistry() {
  static const std::vector<StatKernel> registry = {
      StatKernel{"sum_milli", &stat_sum_milli},
      StatKernel{"mean_milli", &stat_mean_milli},
      StatKernel{"min_milli", &stat_min_milli},
      StatKernel{"max_milli", &stat_max_milli},
      StatKernel{"range_milli", &stat_range_milli},
      StatKernel{"variance_milli", &stat_variance_milli},
      StatKernel{"stddev_milli", &stat_stddev_milli},
      StatKernel{"median_milli", &stat_median_milli},
      StatKernel{"p90_milli", &stat_p90_milli},
      StatKernel{"ewma_milli", &stat_ewma_milli},
      StatKernel{"count_milli", &stat_count_milli},
      StatKernel{"absdev_milli", &stat_absdev_milli},
  };
  return registry;
}

}  // namespace freight
