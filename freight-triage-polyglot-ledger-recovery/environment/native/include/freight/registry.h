#ifndef FREIGHT_REGISTRY_H
#define FREIGHT_REGISTRY_H

// Normative lane / carrier / commodity / tariff registries.
//
// The JSON registries under <root>/environment/data/registry are authoritative.
// The compiled tables in src/tables act as an offline fallback and are covered
// by the cross language selftest.

#include <map>
#include <string>
#include <vector>

namespace freight {

struct LaneRecord {
  std::string laneId;
  std::string originHub;
  std::string destHub;
  std::string serviceClass;
  long long slotCount = 0;
  long long slotCapacityKg = 0;
  long long transitMinutes = 0;
  bool crossDock = false;
};

struct CarrierRecord {
  std::string carrierCode;
  std::string scac;
  std::string legalName;
  std::string region;
  long long insuranceCents = 0;
  bool bonded = false;
};

struct CommodityRecord {
  std::string commodityCode;
  std::string groupCode;
  std::string description;
  long long hazmatDefault = 0;
  long long densityKgM3 = 0;
  bool stackable = false;
};

struct TariffBand {
  std::string band;
  long long minKg = 0;
  long long maxKg = -1;
};

class Registry {
 public:
  bool load(const std::string& registryDir, std::string* error);

  const LaneRecord* lane(const std::string& laneId) const;
  const CarrierRecord* carrier(const std::string& carrierCode) const;
  const CommodityRecord* commodity(const std::string& commodityCode) const;
  const std::vector<TariffBand>& bands() const { return bands_; }
  long long rateCents(const std::string& groupCode, const std::string& band) const;

  size_t laneCount() const { return lanes_.size(); }
  size_t carrierCount() const { return carriers_.size(); }
  size_t commodityCount() const { return commodities_.size(); }

 private:
  std::map<std::string, LaneRecord> lanes_;
  std::map<std::string, CarrierRecord> carriers_;
  std::map<std::string, CommodityRecord> commodities_;
  std::vector<TariffBand> bands_;
  std::map<std::string, long long> rates_;
};

}  // namespace freight

#endif  // FREIGHT_REGISTRY_H
