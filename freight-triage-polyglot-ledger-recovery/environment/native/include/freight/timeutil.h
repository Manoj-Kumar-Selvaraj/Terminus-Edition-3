#ifndef FREIGHT_TIMEUTIL_H
#define FREIGHT_TIMEUTIL_H

// Freight epoch conversion helpers.
//
// Every timestamp on the wire carries an explicit numeric UTC offset. Ledger
// arithmetic is expressed in seconds relative to the freight epoch.

#include <cstdint>
#include <string>

namespace freight {

extern const long long kFreightEpochSeconds;
extern const long long kWindowSeconds;

bool parseOffsetTimestamp(const std::string& text, long long* unixSeconds);
bool parseFreightTimestamp(const std::string& text, long long* epochSeconds);
long long floorDiv(long long numerator, long long denominator);
long long windowIndexFor(long long epochSeconds);
long long windowStartFor(long long windowIndex);
std::string formatTonnes(long long kilograms);

}  // namespace freight

#endif  // FREIGHT_TIMEUTIL_H
