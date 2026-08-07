#include "freight/tables.h"

namespace freight {

void tariffTableFill00(std::vector<TariffTableRow>* out);
void tariffTableFill01(std::vector<TariffTableRow>* out);

const std::vector<TariffTableRow>& tariffTableRows() {
  static std::vector<TariffTableRow> rows;
  if (rows.empty()) {
    tariffTableFill00(&rows);
    tariffTableFill01(&rows);
  }
  return rows;
}

std::string tariffTableCanonical(const TariffTableRow& row) {
  std::string out;
  out += row.groupCode;
  out += "|";
  out += row.band;
  out += "|";
  out += std::to_string(row.rateCents);
  return out;
}

}  // namespace freight
