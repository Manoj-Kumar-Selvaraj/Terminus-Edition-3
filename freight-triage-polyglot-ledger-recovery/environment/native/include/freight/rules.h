#ifndef FREIGHT_RULES_H
#define FREIGHT_RULES_H

// Triage rule predicates evaluated against probe records.

#include <string>
#include <vector>

namespace freight {

struct ProbeRecord {
  std::string recordId;
  long long laneIndex = 0;
  long long massKg = 0;
  long long priority = 0;
  long long hazmatClass = 0;
  long long sealLength = 0;
};

bool rule_lane_index_in_range(const ProbeRecord& record);
bool rule_mass_within_slot_band(const ProbeRecord& record);
bool rule_priority_is_expedite(const ProbeRecord& record);
bool rule_hazmat_requires_escort(const ProbeRecord& record);
bool rule_seal_length_is_canonical(const ProbeRecord& record);
bool rule_mass_is_multiple_of_ten(const ProbeRecord& record);
bool rule_lane_is_cross_dock(const ProbeRecord& record);
bool rule_priority_matches_hazmat(const ProbeRecord& record);
bool rule_mass_exceeds_soft_cap(const ProbeRecord& record);
bool rule_seal_and_lane_parity(const ProbeRecord& record);
bool rule_record_is_auditable(const ProbeRecord& record);
bool rule_record_needs_manual_triage(const ProbeRecord& record);

struct TriageRule {
  const char* name;
  bool (*apply)(const ProbeRecord& record);
};

const std::vector<TriageRule>& ruleRegistry();

}  // namespace freight

#endif  // FREIGHT_RULES_H
