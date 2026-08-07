#include "freight/tables.h"

namespace freight {

void zoneTableFill00(std::vector<ZoneTableRow>* out);
void zoneTableFill01(std::vector<ZoneTableRow>* out);
void zoneTableFill02(std::vector<ZoneTableRow>* out);
void zoneTableFill03(std::vector<ZoneTableRow>* out);
void zoneTableFill04(std::vector<ZoneTableRow>* out);
void zoneTableFill05(std::vector<ZoneTableRow>* out);

const std::vector<ZoneTableRow>& zoneTableRows() {
  static std::vector<ZoneTableRow> rows;
  if (rows.empty()) {
    zoneTableFill00(&rows);
    zoneTableFill01(&rows);
    zoneTableFill02(&rows);
    zoneTableFill03(&rows);
    zoneTableFill04(&rows);
    zoneTableFill05(&rows);
  }
  return rows;
}

std::string zoneTableCanonical(const ZoneTableRow& row) {
  std::string out;
  out += row.zoneKey;
  out += "|";
  out += row.abbrev;
  out += "|";
  out += std::to_string(row.offsetMinutes);
  out += "|";
  out += std::to_string(row.dstShiftMinutes);
  out += "|";
  out += row.hub;
  return out;
}

}  // namespace freight
