#include "freight/tables.h"

namespace freight {

void hazmatTableFill00(std::vector<HazmatTableRow>* out);
void hazmatTableFill01(std::vector<HazmatTableRow>* out);

const std::vector<HazmatTableRow>& hazmatTableRows() {
  static std::vector<HazmatTableRow> rows;
  if (rows.empty()) {
    hazmatTableFill00(&rows);
    hazmatTableFill01(&rows);
  }
  return rows;
}

std::string hazmatTableCanonical(const HazmatTableRow& row) {
  std::string out;
  out += row.ruleId;
  out += "|";
  out += std::to_string(row.hazmatClass);
  out += "|";
  out += std::to_string(row.minEscortPriority);
  out += "|";
  out += row.segregationCode;
  out += "|";
  out += std::to_string(row.maxSlotKg);
  return out;
}

}  // namespace freight
