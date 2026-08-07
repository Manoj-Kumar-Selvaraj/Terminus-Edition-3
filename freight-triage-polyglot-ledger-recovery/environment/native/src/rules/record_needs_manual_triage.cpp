#include "freight/rules.h"

namespace freight {

// Triage predicate: record needs manual triage.
bool rule_record_needs_manual_triage(const ProbeRecord& record) {
  return rule_hazmat_requires_escort(record) || rule_mass_exceeds_soft_cap(record) || !rule_lane_index_in_range(record);
}

}  // namespace freight
