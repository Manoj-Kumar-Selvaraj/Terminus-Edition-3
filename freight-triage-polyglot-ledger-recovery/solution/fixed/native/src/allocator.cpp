#include <algorithm>
#include <map>
#include <string>
#include <vector>

#include "freight/ledger.h"
#include "freight/timeutil.h"

namespace freight {
namespace {

bool allocationOrder(const LedgerEntry& left, const LedgerEntry& right) {
  if (left.priority != right.priority) {
    return left.priority > right.priority;
  }
  if (left.arrivalEpochS != right.arrivalEpochS) {
    return left.arrivalEpochS < right.arrivalEpochS;
  }
  return left.manifestId < right.manifestId;
}

std::string bucketKey(const LedgerEntry& entry) {
  char suffix[32];
  std::snprintf(suffix, sizeof(suffix), "%020lld", entry.windowIndex);
  return entry.laneId + "#" + suffix;
}

}  // namespace

void assignSlots(const Registry& registry, std::vector<LedgerEntry>* entries) {
  std::map<std::string, std::vector<LedgerEntry*> > buckets;
  for (size_t i = 0; i < entries->size(); ++i) {
    LedgerEntry& entry = (*entries)[i];
    if (entry.status != "pending") {
      continue;
    }
    buckets[bucketKey(entry)].push_back(&entry);
  }

  for (std::map<std::string, std::vector<LedgerEntry*> >::iterator it = buckets.begin();
       it != buckets.end(); ++it) {
    std::vector<LedgerEntry*>& bucket = it->second;
    std::sort(bucket.begin(), bucket.end(),
              [](const LedgerEntry* a, const LedgerEntry* b) { return allocationOrder(*a, *b); });
    const LaneRecord* lane = registry.lane(bucket.front()->laneId);
    if (lane == nullptr) {
      continue;
    }
    std::vector<long long> remaining(static_cast<size_t>(lane->slotCount), lane->slotCapacityKg);
    for (size_t i = 0; i < bucket.size(); ++i) {
      LedgerEntry* entry = bucket[i];
      long long need = entry->grossKg;
      bool placed = false;
      for (size_t slot = 0; slot < remaining.size(); ++slot) {
        if (remaining[slot] >= need) {
          remaining[slot] -= need;
          entry->slotIndex = static_cast<long long>(slot) + 1;
          entry->status = "accepted";
          placed = true;
          break;
        }
      }
      if (!placed) {
        entry->slotIndex = 0;
        entry->status = "overflow";
      }
    }
  }
}

}  // namespace freight
