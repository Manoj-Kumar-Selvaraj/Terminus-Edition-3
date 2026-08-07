#include "freight/rules.h"

namespace freight {

// Triage predicate: mass exceeds soft cap.
bool rule_mass_exceeds_soft_cap(const ProbeRecord& record) {
  return record.massKg > 18000;
}

}  // namespace freight
