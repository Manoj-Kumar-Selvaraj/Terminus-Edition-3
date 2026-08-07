#include "freight/ledger.h"

#include <algorithm>
#include <cstdio>
#include <map>
#include <set>

#include "freight/crc.h"
#include "freight/sha256.h"
#include "freight/tariff.h"
#include "freight/timeutil.h"

namespace freight {
namespace {

bool outputOrder(const LedgerEntry& left, const LedgerEntry& right) {
  if (left.laneId != right.laneId) {
    return left.laneId < right.laneId;
  }
  if (left.arrivalEpochS != right.arrivalEpochS) {
    return left.arrivalEpochS < right.arrivalEpochS;
  }
  return left.manifestId < right.manifestId;
}

bool dedupeOrder(const LedgerEntry& left, const LedgerEntry& right) {
  if (left.laneId != right.laneId) {
    return left.laneId < right.laneId;
  }
  if (left.arrivalEpochS != right.arrivalEpochS) {
    return left.arrivalEpochS < right.arrivalEpochS;
  }
  return left.manifestId < right.manifestId;
}

}  // namespace

std::string canonicalLedgerRecord(const LedgerEntry& entry) {
  char buffer[512];
  std::snprintf(buffer, sizeof(buffer), "%s|%s|%lld|%lld|%lld|%lld|%s|%s|%s|%lld\n",
                entry.manifestId.c_str(), entry.laneId.c_str(), entry.windowIndex, entry.slotIndex,
                entry.arrivalEpochS, entry.grossKg, entry.status.c_str(), entry.sealDigest.c_str(),
                entry.tariffBand.c_str(), entry.tariffRateCents);
  return std::string(buffer);
}

std::string ledgerDigest(const std::vector<LedgerEntry>& entries) {
  Sha256 hasher;
  for (size_t i = 0; i < entries.size(); ++i) {
    hasher.update(canonicalLedgerRecord(entries[i]));
  }
  return hasher.hexDigest();
}

Json buildLedgerSnapshot(const Registry& registry, const std::vector<Manifest>& manifests) {
  std::vector<LedgerEntry> entries;
  entries.reserve(manifests.size());

  for (size_t i = 0; i < manifests.size(); ++i) {
    const Manifest& manifest = manifests[i];
    LedgerEntry entry;
    entry.manifestId = manifest.manifestId;
    entry.carrierCode = manifest.carrierCode;
    entry.laneId = manifest.laneId;
    entry.commodityCode = manifest.commodityCode;
    entry.seal = normalizeSeal(manifest.seal);
    entry.sealDigest = sealDigestHex(entry.seal);
    entry.priority = manifest.priority;
    entry.grossKg = manifestGrossKg(manifest);
    entry.pieceCount = static_cast<long long>(manifest.pieces.size());
    entry.hazmatMax = manifestHazmatMax(manifest);
    entry.averagePieceG = manifestAveragePieceGrams(manifest);

    long long epochSeconds = 0;
    if (!parseFreightTimestamp(manifest.arrivalLocal, &epochSeconds)) {
      entry.status = "invalid_arrival";
    }
    entry.arrivalEpochS = epochSeconds;
    entry.windowIndex = windowIndexFor(epochSeconds);

    if (entry.status.empty()) {
      if (registry.lane(manifest.laneId) == nullptr) {
        entry.status = "invalid_lane";
      } else if (registry.carrier(manifest.carrierCode) == nullptr) {
        entry.status = "invalid_carrier";
      } else if (registry.commodity(manifest.commodityCode) == nullptr) {
        entry.status = "invalid_commodity";
      } else {
        entry.status = "pending";
      }
    }
    entries.push_back(entry);
  }

  // Duplicate seal resolution: the earliest entry by (lane, arrival, manifest)
  // keeps the seal, every later holder is quarantined.
  std::map<std::string, std::vector<LedgerEntry*> > sealGroups;
  for (size_t i = 0; i < entries.size(); ++i) {
    if (entries[i].status != "pending") {
      continue;
    }
    const Manifest& manifest = manifests[i];
    (void)manifest;
    sealGroups[entries[i].seal].push_back(&entries[i]);
  }
  for (std::map<std::string, std::vector<LedgerEntry*> >::iterator it = sealGroups.begin();
       it != sealGroups.end(); ++it) {
    std::vector<LedgerEntry*>& group = it->second;
    if (group.size() < 2) {
      continue;
    }
    std::sort(group.begin(), group.end(),
              [](const LedgerEntry* a, const LedgerEntry* b) { return dedupeOrder(*a, *b); });
    for (size_t i = 1; i < group.size(); ++i) {
      group[i]->status = "duplicate_seal";
    }
  }

  for (size_t i = 0; i < entries.size(); ++i) {
    LedgerEntry& entry = entries[i];
    const CommodityRecord* commodity = registry.commodity(entry.commodityCode);
    if (commodity == nullptr) {
      entry.tariffBand = "NA";
      entry.tariffRateCents = 0;
      continue;
    }
    entry.tariffBand = tariffBandFor(registry, entry.grossKg);
    entry.tariffRateCents = registry.rateCents(commodity->groupCode, entry.tariffBand);
  }

  assignSlots(registry, &entries);

  std::sort(entries.begin(), entries.end(), outputOrder);

  Json entryArray = Json::array();
  std::map<std::string, Json> laneAccumulator;
  std::map<std::string, long long> laneAllocatedKg;
  std::map<std::string, long long> laneEntryCount;
  std::map<std::string, long long> laneAcceptedCount;
  std::map<std::string, long long> laneOverflowCount;
  std::map<std::string, long long> laneDuplicateCount;
  std::map<std::string, long long> laneInvalidCount;
  std::map<std::string, std::set<long long> > laneSlots;

  long long acceptedCount = 0;
  long long duplicateCount = 0;
  long long overflowCount = 0;
  long long invalidCount = 0;
  long long grossKgTotal = 0;
  long long acceptedKgTotal = 0;

  for (size_t i = 0; i < entries.size(); ++i) {
    const LedgerEntry& entry = entries[i];
    Json record = Json::object();
    record["arrival_epoch_s"] = Json(entry.arrivalEpochS);
    record["average_piece_g"] = Json(entry.averagePieceG);
    record["carrier_code"] = Json(entry.carrierCode);
    record["commodity_code"] = Json(entry.commodityCode);
    record["gross_kg"] = Json(entry.grossKg);
    record["gross_tonnes"] = Json(formatTonnes(entry.grossKg));
    record["hazmat_max"] = Json(entry.hazmatMax);
    record["lane_id"] = Json(entry.laneId);
    record["manifest_id"] = Json(entry.manifestId);
    record["piece_count"] = Json(entry.pieceCount);
    record["priority"] = Json(entry.priority);
    record["seal"] = Json(entry.seal);
    record["seal_digest"] = Json(entry.sealDigest);
    record["slot_index"] = Json(entry.slotIndex);
    record["status"] = Json(entry.status);
    record["tariff_band"] = Json(entry.tariffBand);
    record["tariff_rate_cents"] = Json(entry.tariffRateCents);
    record["window_index"] = Json(entry.windowIndex);
    entryArray.push(record);

    grossKgTotal += entry.grossKg;
    laneEntryCount[entry.laneId] += 1;
    if (entry.status == "accepted") {
      acceptedCount += 1;
      acceptedKgTotal += entry.grossKg;
      laneAcceptedCount[entry.laneId] += 1;
      laneAllocatedKg[entry.laneId] += entry.grossKg;
      if (entry.slotIndex > 0) {
        laneSlots[entry.laneId].insert(entry.slotIndex);
      }
    } else if (entry.status == "duplicate_seal") {
      duplicateCount += 1;
      laneDuplicateCount[entry.laneId] += 1;
    } else if (entry.status == "overflow") {
      overflowCount += 1;
      laneOverflowCount[entry.laneId] += 1;
    } else {
      invalidCount += 1;
      laneInvalidCount[entry.laneId] += 1;
    }
  }

  Json laneTotals = Json::array();
  for (std::map<std::string, long long>::const_iterator it = laneEntryCount.begin();
       it != laneEntryCount.end(); ++it) {
    const std::string& laneId = it->first;
    Json row = Json::object();
    row["accepted_count"] = Json(laneAcceptedCount[laneId]);
    row["allocated_kg"] = Json(laneAllocatedKg[laneId]);
    row["allocated_tonnes"] = Json(formatTonnes(laneAllocatedKg[laneId]));
    row["duplicate_seal_count"] = Json(laneDuplicateCount[laneId]);
    row["entry_count"] = Json(it->second);
    row["invalid_count"] = Json(laneInvalidCount[laneId]);
    row["lane_id"] = Json(laneId);
    row["overflow_count"] = Json(laneOverflowCount[laneId]);
    row["slots_used"] = Json(static_cast<long long>(laneSlots[laneId].size()));
    laneTotals.push(row);
  }

  Json totals = Json::object();
  totals["accepted_count"] = Json(acceptedCount);
  totals["accepted_kg"] = Json(acceptedKgTotal);
  totals["accepted_tonnes"] = Json(formatTonnes(acceptedKgTotal));
  totals["duplicate_seal_count"] = Json(duplicateCount);
  totals["gross_kg"] = Json(grossKgTotal);
  totals["gross_tonnes"] = Json(formatTonnes(grossKgTotal));
  totals["invalid_count"] = Json(invalidCount);
  totals["manifest_count"] = Json(static_cast<long long>(entries.size()));
  totals["overflow_count"] = Json(overflowCount);

  Json snapshot = Json::object();
  snapshot["entries"] = entryArray;
  snapshot["epoch_base_s"] = Json(kFreightEpochSeconds);
  snapshot["generator"] = Json(std::string("freightctl"));
  snapshot["lane_totals"] = laneTotals;
  snapshot["ledger_digest"] = Json(ledgerDigest(entries));
  snapshot["schema_version"] = Json(std::string("freight-ledger/2"));
  snapshot["totals"] = totals;
  snapshot["window_seconds"] = Json(kWindowSeconds);
  return snapshot;
}

}  // namespace freight
