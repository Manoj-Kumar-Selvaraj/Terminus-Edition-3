#include "freight/rules.h"

namespace freight {

// Triage predicate: record is auditable.
bool rule_record_is_auditable(const ProbeRecord& record) {
  return rule_lane_index_in_range(record) && rule_seal_length_is_canonical(record) && !rule_mass_exceeds_soft_cap(record);
}

}  // namespace freight
