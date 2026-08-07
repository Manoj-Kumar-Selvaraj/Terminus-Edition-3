#ifndef FREIGHT_TABLES_H
#define FREIGHT_TABLES_H

// Compiled fallback registries.
//
// These tables mirror the JSON registries under environment/data/registry and
// are the offline source of truth when the JSON registries are unavailable.
// The cross language selftest digests them so drift is caught immediately.

#include <string>
#include <vector>

namespace freight {

struct LaneTableRow {
  std::string laneId;
  std::string originHub;
  std::string destHub;
  std::string serviceClass;
  long long slotCount;
  long long slotCapacityKg;
  long long transitMinutes;
  bool crossDock;
};

const std::vector<LaneTableRow>& laneTableRows();
std::string laneTableCanonical(const LaneTableRow& row);

struct CarrierTableRow {
  std::string carrierCode;
  std::string scac;
  std::string legalName;
  std::string region;
  long long insuranceCents;
  bool bonded;
};

const std::vector<CarrierTableRow>& carrierTableRows();
std::string carrierTableCanonical(const CarrierTableRow& row);

struct CommodityTableRow {
  std::string commodityCode;
  std::string groupCode;
  std::string description;
  long long hazmatDefault;
  long long densityKgM3;
  bool stackable;
};

const std::vector<CommodityTableRow>& commodityTableRows();
std::string commodityTableCanonical(const CommodityTableRow& row);

struct TariffTableRow {
  std::string groupCode;
  std::string band;
  long long rateCents;
};

const std::vector<TariffTableRow>& tariffTableRows();
std::string tariffTableCanonical(const TariffTableRow& row);

struct ZoneTableRow {
  std::string zoneKey;
  std::string abbrev;
  long long offsetMinutes;
  long long dstShiftMinutes;
  std::string hub;
};

const std::vector<ZoneTableRow>& zoneTableRows();
std::string zoneTableCanonical(const ZoneTableRow& row);

struct HazmatTableRow {
  std::string ruleId;
  long long hazmatClass;
  long long minEscortPriority;
  std::string segregationCode;
  long long maxSlotKg;
};

const std::vector<HazmatTableRow>& hazmatTableRows();
std::string hazmatTableCanonical(const HazmatTableRow& row);

}  // namespace freight

#endif  // FREIGHT_TABLES_H
