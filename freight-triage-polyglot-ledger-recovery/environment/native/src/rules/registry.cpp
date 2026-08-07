#include "freight/rules.h"

namespace freight {

const std::vector<TriageRule>& ruleRegistry() {
  static const std::vector<TriageRule> registry = {
      TriageRule{"lane_index_in_range", &rule_lane_index_in_range},
      TriageRule{"mass_within_slot_band", &rule_mass_within_slot_band},
      TriageRule{"priority_is_expedite", &rule_priority_is_expedite},
      TriageRule{"hazmat_requires_escort", &rule_hazmat_requires_escort},
      TriageRule{"seal_length_is_canonical", &rule_seal_length_is_canonical},
      TriageRule{"mass_is_multiple_of_ten", &rule_mass_is_multiple_of_ten},
      TriageRule{"lane_is_cross_dock", &rule_lane_is_cross_dock},
      TriageRule{"priority_matches_hazmat", &rule_priority_matches_hazmat},
      TriageRule{"mass_exceeds_soft_cap", &rule_mass_exceeds_soft_cap},
      TriageRule{"seal_and_lane_parity", &rule_seal_and_lane_parity},
      TriageRule{"record_is_auditable", &rule_record_is_auditable},
      TriageRule{"record_needs_manual_triage", &rule_record_needs_manual_triage},
  };
  return registry;
}

}  // namespace freight
