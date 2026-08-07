#include "freight/tables.h"

namespace freight {

void commodityTableFill00(std::vector<CommodityTableRow>* out);
void commodityTableFill01(std::vector<CommodityTableRow>* out);
void commodityTableFill02(std::vector<CommodityTableRow>* out);
void commodityTableFill03(std::vector<CommodityTableRow>* out);
void commodityTableFill04(std::vector<CommodityTableRow>* out);
void commodityTableFill05(std::vector<CommodityTableRow>* out);
void commodityTableFill06(std::vector<CommodityTableRow>* out);
void commodityTableFill07(std::vector<CommodityTableRow>* out);
void commodityTableFill08(std::vector<CommodityTableRow>* out);
void commodityTableFill09(std::vector<CommodityTableRow>* out);
void commodityTableFill10(std::vector<CommodityTableRow>* out);
void commodityTableFill11(std::vector<CommodityTableRow>* out);
void commodityTableFill12(std::vector<CommodityTableRow>* out);
void commodityTableFill13(std::vector<CommodityTableRow>* out);
void commodityTableFill14(std::vector<CommodityTableRow>* out);
void commodityTableFill15(std::vector<CommodityTableRow>* out);
void commodityTableFill16(std::vector<CommodityTableRow>* out);
void commodityTableFill17(std::vector<CommodityTableRow>* out);

const std::vector<CommodityTableRow>& commodityTableRows() {
  static std::vector<CommodityTableRow> rows;
  if (rows.empty()) {
    commodityTableFill00(&rows);
    commodityTableFill01(&rows);
    commodityTableFill02(&rows);
    commodityTableFill03(&rows);
    commodityTableFill04(&rows);
    commodityTableFill05(&rows);
    commodityTableFill06(&rows);
    commodityTableFill07(&rows);
    commodityTableFill08(&rows);
    commodityTableFill09(&rows);
    commodityTableFill10(&rows);
    commodityTableFill11(&rows);
    commodityTableFill12(&rows);
    commodityTableFill13(&rows);
    commodityTableFill14(&rows);
    commodityTableFill15(&rows);
    commodityTableFill16(&rows);
    commodityTableFill17(&rows);
  }
  return rows;
}

std::string commodityTableCanonical(const CommodityTableRow& row) {
  std::string out;
  out += row.commodityCode;
  out += "|";
  out += row.groupCode;
  out += "|";
  out += row.description;
  out += "|";
  out += std::to_string(row.hazmatDefault);
  out += "|";
  out += std::to_string(row.densityKgM3);
  out += "|";
  out += row.stackable ? "1" : "0";
  return out;
}

}  // namespace freight
