#include "freight/tables.h"

namespace freight {

void carrierTableFill00(std::vector<CarrierTableRow>* out);
void carrierTableFill01(std::vector<CarrierTableRow>* out);
void carrierTableFill02(std::vector<CarrierTableRow>* out);
void carrierTableFill03(std::vector<CarrierTableRow>* out);
void carrierTableFill04(std::vector<CarrierTableRow>* out);
void carrierTableFill05(std::vector<CarrierTableRow>* out);
void carrierTableFill06(std::vector<CarrierTableRow>* out);
void carrierTableFill07(std::vector<CarrierTableRow>* out);

const std::vector<CarrierTableRow>& carrierTableRows() {
  static std::vector<CarrierTableRow> rows;
  if (rows.empty()) {
    carrierTableFill00(&rows);
    carrierTableFill01(&rows);
    carrierTableFill02(&rows);
    carrierTableFill03(&rows);
    carrierTableFill04(&rows);
    carrierTableFill05(&rows);
    carrierTableFill06(&rows);
    carrierTableFill07(&rows);
  }
  return rows;
}

std::string carrierTableCanonical(const CarrierTableRow& row) {
  std::string out;
  out += row.carrierCode;
  out += "|";
  out += row.scac;
  out += "|";
  out += row.legalName;
  out += "|";
  out += row.region;
  out += "|";
  out += std::to_string(row.insuranceCents);
  out += "|";
  out += row.bonded ? "1" : "0";
  return out;
}

}  // namespace freight
