#include "freight/rules.h"

namespace freight {

// Triage predicate: seal length is canonical.
bool rule_seal_length_is_canonical(const ProbeRecord& record) {
  return record.sealLength == 9;
}

}  // namespace freight
