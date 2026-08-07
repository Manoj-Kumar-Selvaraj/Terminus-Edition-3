#ifndef FREIGHT_STATS_H
#define FREIGHT_STATS_H

// Fixed point windowed statistics. All results are scaled by 1000 and use
// floor division so C++, Java and Go agree bit for bit.

#include <string>
#include <vector>

namespace freight {

long long statFloorDiv(long long numerator, long long denominator);
long long statIntegerSqrt(long long value);

long long stat_sum_milli(const std::vector<long long>& series);
long long stat_mean_milli(const std::vector<long long>& series);
long long stat_min_milli(const std::vector<long long>& series);
long long stat_max_milli(const std::vector<long long>& series);
long long stat_range_milli(const std::vector<long long>& series);
long long stat_variance_milli(const std::vector<long long>& series);
long long stat_stddev_milli(const std::vector<long long>& series);
long long stat_median_milli(const std::vector<long long>& series);
long long stat_p90_milli(const std::vector<long long>& series);
long long stat_ewma_milli(const std::vector<long long>& series);
long long stat_count_milli(const std::vector<long long>& series);
long long stat_absdev_milli(const std::vector<long long>& series);

struct StatKernel {
  const char* name;
  long long (*apply)(const std::vector<long long>& series);
};

const std::vector<StatKernel>& statRegistry();

}  // namespace freight

#endif  // FREIGHT_STATS_H
