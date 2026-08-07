#include "freight/rules.h"

namespace freight {

// Triage predicate: priority matches hazmat.
bool rule_priority_matches_hazmat(const ProbeRecord& record) {
  return record.priority == record.hazmatClass % 5;
}

}  // namespace freight
