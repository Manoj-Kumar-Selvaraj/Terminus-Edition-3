#ifndef FREIGHT_SELFTEST_H
#define FREIGHT_SELFTEST_H

// Cross language conformance probe.
//
// Every language in the freight stack runs the same probe corpus through the
// same algorithm families. The resulting family digests must agree exactly.

#include <string>
#include <vector>

#include "freight/json.h"
#include "freight/rules.h"

namespace freight {

unsigned int probeMix32(unsigned int seed);
std::string probeString(int index);
std::vector<long long> probeSeries(int series);
std::vector<ProbeRecord> probeRecords();

Json buildSelftestReport();

}  // namespace freight

#endif  // FREIGHT_SELFTEST_H
