#ifndef FREIGHT_LEDGER_H
#define FREIGHT_LEDGER_H

// Ledger entry model, slot allocation and snapshot serialization.

#include <string>
#include <vector>

#include "freight/json.h"
#include "freight/manifest.h"
#include "freight/registry.h"

namespace freight {

struct LedgerEntry {
  std::string manifestId;
  std::string carrierCode;
  std::string laneId;
  std::string commodityCode;
  std::string seal;
  std::string sealDigest;
  std::string status;
  std::string tariffBand;
  long long arrivalEpochS = 0;
  long long windowIndex = 0;
  long long slotIndex = 0;
  long long grossKg = 0;
  long long pieceCount = 0;
  long long hazmatMax = 0;
  long long priority = 0;
  long long averagePieceG = 0;
  long long tariffRateCents = 0;
};

void assignSlots(const Registry& registry, std::vector<LedgerEntry>* entries);
std::string canonicalLedgerRecord(const LedgerEntry& entry);
std::string ledgerDigest(const std::vector<LedgerEntry>& entries);
Json buildLedgerSnapshot(const Registry& registry, const std::vector<Manifest>& manifests);

}  // namespace freight

#endif  // FREIGHT_LEDGER_H
