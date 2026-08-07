#ifndef FREIGHT_TARIFF_H
#define FREIGHT_TARIFF_H

// Tariff band resolution over the normative band table.

#include <string>

#include "freight/registry.h"

namespace freight {

std::string tariffBandFor(const Registry& registry, long long grossKg);
long long accruedCents(long long rateCents, long long billableKg);

}  // namespace freight

#endif  // FREIGHT_TARIFF_H
