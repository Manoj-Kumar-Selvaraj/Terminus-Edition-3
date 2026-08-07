#include "freight/rules.h"

namespace freight {

// Triage predicate: lane is cross dock.
bool rule_lane_is_cross_dock(const ProbeRecord& record) {
  return record.laneIndex % 7 == 0;
}

}  // namespace freight
