#include "freight/rules.h"

namespace freight {

// Triage predicate: lane index in range.
bool rule_lane_index_in_range(const ProbeRecord& record) {
  return record.laneIndex >= 0 && record.laneIndex < 360;
}

}  // namespace freight
