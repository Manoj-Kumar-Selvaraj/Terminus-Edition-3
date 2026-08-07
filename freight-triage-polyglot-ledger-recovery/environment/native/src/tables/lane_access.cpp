#include "freight/tables.h"

namespace freight {

void laneTableFill00(std::vector<LaneTableRow>* out);
void laneTableFill01(std::vector<LaneTableRow>* out);
void laneTableFill02(std::vector<LaneTableRow>* out);
void laneTableFill03(std::vector<LaneTableRow>* out);
void laneTableFill04(std::vector<LaneTableRow>* out);
void laneTableFill05(std::vector<LaneTableRow>* out);
void laneTableFill06(std::vector<LaneTableRow>* out);
void laneTableFill07(std::vector<LaneTableRow>* out);
void laneTableFill08(std::vector<LaneTableRow>* out);

const std::vector<LaneTableRow>& laneTableRows() {
  static std::vector<LaneTableRow> rows;
  if (rows.empty()) {
    laneTableFill00(&rows);
    laneTableFill01(&rows);
    laneTableFill02(&rows);
    laneTableFill03(&rows);
    laneTableFill04(&rows);
    laneTableFill05(&rows);
    laneTableFill06(&rows);
    laneTableFill07(&rows);
    laneTableFill08(&rows);
  }
  return rows;
}

std::string laneTableCanonical(const LaneTableRow& row) {
  std::string out;
  out += row.laneId;
  out += "|";
  out += row.originHub;
  out += "|";
  out += row.destHub;
  out += "|";
  out += row.serviceClass;
  out += "|";
  out += std::to_string(row.slotCount);
  out += "|";
  out += std::to_string(row.slotCapacityKg);
  out += "|";
  out += std::to_string(row.transitMinutes);
  out += "|";
  out += row.crossDock ? "1" : "0";
  return out;
}

}  // namespace freight
