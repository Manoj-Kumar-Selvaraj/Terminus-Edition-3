#include "freight/tables.h"

namespace freight {

// lane table rows 0..59.
void laneTableFill00(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-000", "HOU", "PDX", "standard", 1, 8000, 360, true});
  out->push_back(LaneTableRow{"LN-001", "IND", "OKC", "standard", 2, 9500, 405, false});
  out->push_back(LaneTableRow{"LN-002", "CHI", "DTW", "flatbed", 3, 11000, 450, false});
  out->push_back(LaneTableRow{"LN-003", "IND", "MSP", "reefer", 4, 12500, 495, false});
  out->push_back(LaneTableRow{"LN-004", "PHX", "PDX", "intermodal", 5, 14000, 540, false});
  out->push_back(LaneTableRow{"LN-005", "SLC", "OKC", "standard", 6, 15500, 585, false});
  out->push_back(LaneTableRow{"LN-006", "YVR", "NSH", "bonded", 1, 17000, 630, false});
  out->push_back(LaneTableRow{"LN-007", "NSH", "NSH", "intermodal", 2, 18500, 675, true});
  out->push_back(LaneTableRow{"LN-008", "CHI", "PDX", "reefer", 3, 20000, 720, false});
  out->push_back(LaneTableRow{"LN-009", "JAX", "CHI", "expedite", 4, 21500, 765, false});
  out->push_back(LaneTableRow{"LN-010", "YVR", "LAX", "standard", 5, 23000, 810, false});
  out->push_back(LaneTableRow{"LN-011", "RNO", "RNO", "expedite", 6, 8000, 855, false});
  out->push_back(LaneTableRow{"LN-012", "ATL", "DTW", "expedite", 1, 9500, 900, false});
  out->push_back(LaneTableRow{"LN-013", "HOU", "DFW", "reefer", 2, 11000, 945, false});
  out->push_back(LaneTableRow{"LN-014", "SLC", "OKC", "reefer", 3, 12500, 990, true});
  out->push_back(LaneTableRow{"LN-015", "JAX", "RNO", "intermodal", 4, 14000, 1035, false});
  out->push_back(LaneTableRow{"LN-016", "DEN", "TPA", "expedite", 5, 15500, 1080, false});
  out->push_back(LaneTableRow{"LN-017", "RNO", "LAX", "standard", 6, 17000, 1125, false});
  out->push_back(LaneTableRow{"LN-018", "MSP", "PDX", "bonded", 1, 18500, 1170, false});
  out->push_back(LaneTableRow{"LN-019", "JAX", "JAX", "intermodal", 2, 20000, 1215, false});
  out->push_back(LaneTableRow{"LN-020", "RNO", "DFW", "expedite", 3, 21500, 1260, false});
  out->push_back(LaneTableRow{"LN-021", "KCK", "IND", "reefer", 4, 23000, 1305, true});
  out->push_back(LaneTableRow{"LN-022", "RNO", "MEM", "standard", 5, 8000, 1350, false});
  out->push_back(LaneTableRow{"LN-023", "DFW", "TPA", "flatbed", 6, 9500, 1395, false});
  out->push_back(LaneTableRow{"LN-024", "ATL", "TPA", "bonded", 1, 11000, 1440, false});
  out->push_back(LaneTableRow{"LN-025", "ATL", "IND", "standard", 2, 12500, 1485, false});
  out->push_back(LaneTableRow{"LN-026", "KCK", "DTW", "flatbed", 3, 14000, 1530, false});
  out->push_back(LaneTableRow{"LN-027", "JAX", "RNO", "expedite", 4, 15500, 1575, false});
  out->push_back(LaneTableRow{"LN-028", "YYZ", "CHI", "flatbed", 5, 17000, 1620, true});
  out->push_back(LaneTableRow{"LN-029", "STL", "RNO", "intermodal", 6, 18500, 1665, false});
  out->push_back(LaneTableRow{"LN-030", "RNO", "MSP", "bonded", 1, 20000, 1710, false});
  out->push_back(LaneTableRow{"LN-031", "LAX", "LAX", "standard", 2, 21500, 1755, false});
  out->push_back(LaneTableRow{"LN-032", "SLC", "JAX", "bonded", 3, 23000, 1800, false});
  out->push_back(LaneTableRow{"LN-033", "LAX", "OKC", "reefer", 4, 8000, 1845, false});
  out->push_back(LaneTableRow{"LN-034", "TPA", "MEM", "standard", 5, 9500, 1890, false});
  out->push_back(LaneTableRow{"LN-035", "STL", "YYZ", "flatbed", 6, 11000, 1935, true});
  out->push_back(LaneTableRow{"LN-036", "YVR", "BOS", "expedite", 1, 12500, 1980, false});
  out->push_back(LaneTableRow{"LN-037", "STL", "MEM", "reefer", 2, 14000, 2025, false});
  out->push_back(LaneTableRow{"LN-038", "YYZ", "YVR", "intermodal", 3, 15500, 2070, false});
  out->push_back(LaneTableRow{"LN-039", "CHI", "DFW", "standard", 4, 17000, 2115, false});
  out->push_back(LaneTableRow{"LN-040", "BOS", "TPA", "flatbed", 5, 18500, 360, false});
  out->push_back(LaneTableRow{"LN-041", "STL", "BOS", "flatbed", 6, 20000, 405, false});
  out->push_back(LaneTableRow{"LN-042", "PHX", "TPA", "intermodal", 1, 21500, 450, true});
  out->push_back(LaneTableRow{"LN-043", "RNO", "RNO", "expedite", 2, 23000, 495, false});
  out->push_back(LaneTableRow{"LN-044", "CHI", "PDX", "reefer", 3, 8000, 540, false});
  out->push_back(LaneTableRow{"LN-045", "PHX", "DTW", "flatbed", 4, 9500, 585, false});
  out->push_back(LaneTableRow{"LN-046", "HOU", "DFW", "reefer", 5, 11000, 630, false});
  out->push_back(LaneTableRow{"LN-047", "ATL", "SLC", "bonded", 6, 12500, 675, false});
  out->push_back(LaneTableRow{"LN-048", "SEA", "DTW", "flatbed", 1, 14000, 720, false});
  out->push_back(LaneTableRow{"LN-049", "YVR", "RNO", "intermodal", 2, 15500, 765, true});
  out->push_back(LaneTableRow{"LN-050", "STL", "KCK", "intermodal", 3, 17000, 810, false});
  out->push_back(LaneTableRow{"LN-051", "STL", "NSH", "standard", 4, 18500, 855, false});
  out->push_back(LaneTableRow{"LN-052", "OKC", "DEN", "flatbed", 5, 20000, 900, false});
  out->push_back(LaneTableRow{"LN-053", "TPA", "JAX", "reefer", 6, 21500, 945, false});
  out->push_back(LaneTableRow{"LN-054", "MSP", "DEN", "flatbed", 1, 23000, 990, false});
  out->push_back(LaneTableRow{"LN-055", "YVR", "TPA", "expedite", 2, 8000, 1035, false});
  out->push_back(LaneTableRow{"LN-056", "TPA", "YYZ", "flatbed", 3, 9500, 1080, true});
  out->push_back(LaneTableRow{"LN-057", "BOS", "TPA", "flatbed", 4, 11000, 1125, false});
  out->push_back(LaneTableRow{"LN-058", "TPA", "MSP", "reefer", 5, 12500, 1170, false});
  out->push_back(LaneTableRow{"LN-059", "MEM", "NSH", "standard", 6, 14000, 1215, false});
}

}  // namespace freight
