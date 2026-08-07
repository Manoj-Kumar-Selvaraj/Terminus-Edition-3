#include "freight/rules.h"

namespace freight {

// Triage predicate: mass within slot band.
bool rule_mass_within_slot_band(const ProbeRecord& record) {
  return record.massKg >= 500 && record.massKg <= 24000;
}

}  // namespace freight
