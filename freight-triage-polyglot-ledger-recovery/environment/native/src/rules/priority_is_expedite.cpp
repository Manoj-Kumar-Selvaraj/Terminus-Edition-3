#include "freight/rules.h"

namespace freight {

// Triage predicate: priority is expedite.
bool rule_priority_is_expedite(const ProbeRecord& record) {
  return record.priority >= 3;
}

}  // namespace freight
