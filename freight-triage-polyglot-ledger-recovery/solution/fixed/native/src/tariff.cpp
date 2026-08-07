#include "freight/tariff.h"

namespace freight {

std::string tariffBandFor(const Registry& registry, long long grossKg) {
  const std::vector<TariffBand>& bands = registry.bands();
  for (size_t i = 0; i < bands.size(); ++i) {
    const TariffBand& band = bands[i];
    bool aboveFloor = grossKg >= band.minKg;
    bool belowCeiling = band.maxKg < 0 || grossKg < band.maxKg;
    if (aboveFloor && belowCeiling) {
      return band.band;
    }
  }
  return "NA";
}

long long accruedCents(long long rateCents, long long billableKg) {
  return (rateCents * billableKg + 500) / 1000;
}

}  // namespace freight
