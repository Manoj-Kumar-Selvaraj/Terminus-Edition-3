#include "freight/rules.h"

namespace freight {

// Triage predicate: seal and lane parity.
bool rule_seal_and_lane_parity(const ProbeRecord& record) {
  return (record.sealLength + record.laneIndex) % 2 == 0;
}

}  // namespace freight
