#include "freight/registry.h"

#include "freight/json.h"

namespace freight {

bool Registry::load(const std::string& registryDir, std::string* error) {
  Json lanesDoc;
  if (!Json::parseFile(registryDir + "/lanes.json", &lanesDoc, error)) {
    return false;
  }
  const JsonArray& lanes = lanesDoc.at("lanes").items();
  for (size_t i = 0; i < lanes.size(); ++i) {
    const Json& row = lanes[i];
    LaneRecord record;
    record.laneId = row.at("lane_id").asString();
    record.originHub = row.at("origin_hub").asString();
    record.destHub = row.at("dest_hub").asString();
    record.serviceClass = row.at("service_class").asString();
    record.slotCount = row.at("slot_count").asInt();
    record.slotCapacityKg = row.at("slot_capacity_kg").asInt();
    record.transitMinutes = row.at("transit_minutes").asInt();
    record.crossDock = row.at("cross_dock").asBool();
    lanes_[record.laneId] = record;
  }

  Json carriersDoc;
  if (!Json::parseFile(registryDir + "/carriers.json", &carriersDoc, error)) {
    return false;
  }
  const JsonArray& carriers = carriersDoc.at("carriers").items();
  for (size_t i = 0; i < carriers.size(); ++i) {
    const Json& row = carriers[i];
    CarrierRecord record;
    record.carrierCode = row.at("carrier_code").asString();
    record.scac = row.at("scac").asString();
    record.legalName = row.at("legal_name").asString();
    record.region = row.at("region").asString();
    record.insuranceCents = row.at("insurance_cents").asInt();
    record.bonded = row.at("bonded").asBool();
    carriers_[record.carrierCode] = record;
  }

  Json commoditiesDoc;
  if (!Json::parseFile(registryDir + "/commodities.json", &commoditiesDoc, error)) {
    return false;
  }
  const JsonArray& commodities = commoditiesDoc.at("commodities").items();
  for (size_t i = 0; i < commodities.size(); ++i) {
    const Json& row = commodities[i];
    CommodityRecord record;
    record.commodityCode = row.at("commodity_code").asString();
    record.groupCode = row.at("group_code").asString();
    record.description = row.at("description").asString();
    record.hazmatDefault = row.at("hazmat_default").asInt();
    record.densityKgM3 = row.at("density_kg_m3").asInt();
    record.stackable = row.at("stackable").asBool();
    commodities_[record.commodityCode] = record;
  }

  Json tariffDoc;
  if (!Json::parseFile(registryDir + "/tariff.json", &tariffDoc, error)) {
    return false;
  }
  const JsonArray& bands = tariffDoc.at("bands").items();
  for (size_t i = 0; i < bands.size(); ++i) {
    TariffBand band;
    band.band = bands[i].at("band").asString();
    band.minKg = bands[i].at("min_kg").asInt();
    band.maxKg = bands[i].at("max_kg").asInt(-1);
    bands_.push_back(band);
  }
  const JsonArray& rates = tariffDoc.at("rates").items();
  for (size_t i = 0; i < rates.size(); ++i) {
    const std::string key = rates[i].at("group_code").asString() + "/" + rates[i].at("band").asString();
    rates_[key] = rates[i].at("rate_cents").asInt();
  }
  return true;
}

const LaneRecord* Registry::lane(const std::string& laneId) const {
  std::map<std::string, LaneRecord>::const_iterator it = lanes_.find(laneId);
  return it == lanes_.end() ? nullptr : &it->second;
}

const CarrierRecord* Registry::carrier(const std::string& carrierCode) const {
  std::map<std::string, CarrierRecord>::const_iterator it = carriers_.find(carrierCode);
  return it == carriers_.end() ? nullptr : &it->second;
}

const CommodityRecord* Registry::commodity(const std::string& commodityCode) const {
  std::map<std::string, CommodityRecord>::const_iterator it = commodities_.find(commodityCode);
  return it == commodities_.end() ? nullptr : &it->second;
}

long long Registry::rateCents(const std::string& groupCode, const std::string& band) const {
  std::map<std::string, long long>::const_iterator it = rates_.find(groupCode + "/" + band);
  return it == rates_.end() ? 0 : it->second;
}

}  // namespace freight
