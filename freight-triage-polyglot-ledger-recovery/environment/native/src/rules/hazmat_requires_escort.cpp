#include "freight/rules.h"

namespace freight {

// Triage predicate: hazmat requires escort.
bool rule_hazmat_requires_escort(const ProbeRecord& record) {
  return record.hazmatClass >= 3 && record.priority < 2;
}

}  // namespace freight
