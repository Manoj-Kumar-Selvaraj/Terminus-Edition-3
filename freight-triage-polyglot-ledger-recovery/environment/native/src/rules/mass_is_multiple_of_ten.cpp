#include "freight/rules.h"

namespace freight {

// Triage predicate: mass is multiple of ten.
bool rule_mass_is_multiple_of_ten(const ProbeRecord& record) {
  return record.massKg % 10 == 0;
}

}  // namespace freight
