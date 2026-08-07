#include "freight/tables.h"

namespace freight {

// lane table rows 300..359.
void laneTableFill05(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-300", "DFW", "ATL", "flatbed", 1, 12500, 1260, false});
  out->push_back(LaneTableRow{"LN-301", "CHI", "MSP", "standard", 2, 14000, 1305, true});
  out->push_back(LaneTableRow{"LN-302", "KCK", "NSH", "reefer", 3, 15500, 1350, false});
  out->push_back(LaneTableRow{"LN-303", "TPA", "ATL", "reefer", 4, 17000, 1395, false});
  out->push_back(LaneTableRow{"LN-304", "CHI", "NSH", "reefer", 5, 18500, 1440, false});
  out->push_back(LaneTableRow{"LN-305", "JAX", "SEA", "flatbed", 6, 20000, 1485, false});
  out->push_back(LaneTableRow{"LN-306", "DTW", "OKC", "bonded", 1, 21500, 1530, false});
  out->push_back(LaneTableRow{"LN-307", "PHX", "YYZ", "flatbed", 2, 23000, 1575, false});
  out->push_back(LaneTableRow{"LN-308", "YVR", "JAX", "bonded", 3, 8000, 1620, true});
  out->push_back(LaneTableRow{"LN-309", "STL", "YVR", "bonded", 4, 9500, 1665, false});
  out->push_back(LaneTableRow{"LN-310", "RNO", "YYZ", "bonded", 5, 11000, 1710, false});
  out->push_back(LaneTableRow{"LN-311", "KCK", "JAX", "reefer", 6, 12500, 1755, false});
  out->push_back(LaneTableRow{"LN-312", "BOS", "PDX", "intermodal", 1, 14000, 1800, false});
  out->push_back(LaneTableRow{"LN-313", "MEM", "PDX", "reefer", 2, 15500, 1845, false});
  out->push_back(LaneTableRow{"LN-314", "MSP", "STL", "flatbed", 3, 17000, 1890, false});
  out->push_back(LaneTableRow{"LN-315", "YVR", "RNO", "flatbed", 4, 18500, 1935, true});
  out->push_back(LaneTableRow{"LN-316", "JAX", "DEN", "flatbed", 5, 20000, 1980, false});
  out->push_back(LaneTableRow{"LN-317", "YVR", "DTW", "flatbed", 6, 21500, 2025, false});
  out->push_back(LaneTableRow{"LN-318", "CHI", "RNO", "flatbed", 1, 23000, 2070, false});
  out->push_back(LaneTableRow{"LN-319", "DTW", "RNO", "expedite", 2, 8000, 2115, false});
  out->push_back(LaneTableRow{"LN-320", "BOS", "LAX", "standard", 3, 9500, 360, false});
  out->push_back(LaneTableRow{"LN-321", "TPA", "MEM", "reefer", 4, 11000, 405, false});
  out->push_back(LaneTableRow{"LN-322", "RNO", "PHX", "flatbed", 5, 12500, 450, true});
  out->push_back(LaneTableRow{"LN-323", "RNO", "STL", "flatbed", 6, 14000, 495, false});
  out->push_back(LaneTableRow{"LN-324", "PHX", "LAX", "reefer", 1, 15500, 540, false});
  out->push_back(LaneTableRow{"LN-325", "HOU", "DEN", "standard", 2, 17000, 585, false});
  out->push_back(LaneTableRow{"LN-326", "HOU", "ATL", "reefer", 3, 18500, 630, false});
  out->push_back(LaneTableRow{"LN-327", "DTW", "KCK", "bonded", 4, 20000, 675, false});
  out->push_back(LaneTableRow{"LN-328", "SEA", "SEA", "expedite", 5, 21500, 720, false});
  out->push_back(LaneTableRow{"LN-329", "DTW", "SLC", "intermodal", 6, 23000, 765, true});
  out->push_back(LaneTableRow{"LN-330", "CHI", "OKC", "standard", 1, 8000, 810, false});
  out->push_back(LaneTableRow{"LN-331", "BOS", "DTW", "expedite", 2, 9500, 855, false});
  out->push_back(LaneTableRow{"LN-332", "JAX", "BOS", "flatbed", 3, 11000, 900, false});
  out->push_back(LaneTableRow{"LN-333", "NSH", "LAX", "reefer", 4, 12500, 945, false});
  out->push_back(LaneTableRow{"LN-334", "MSP", "BOS", "flatbed", 5, 14000, 990, false});
  out->push_back(LaneTableRow{"LN-335", "YVR", "DEN", "flatbed", 6, 15500, 1035, false});
  out->push_back(LaneTableRow{"LN-336", "YVR", "SEA", "flatbed", 1, 17000, 1080, true});
  out->push_back(LaneTableRow{"LN-337", "PHX", "BOS", "standard", 2, 18500, 1125, false});
  out->push_back(LaneTableRow{"LN-338", "OKC", "PDX", "reefer", 3, 20000, 1170, false});
  out->push_back(LaneTableRow{"LN-339", "SEA", "HOU", "standard", 4, 21500, 1215, false});
  out->push_back(LaneTableRow{"LN-340", "PDX", "MEM", "bonded", 5, 23000, 1260, false});
  out->push_back(LaneTableRow{"LN-341", "KCK", "BOS", "flatbed", 6, 8000, 1305, false});
  out->push_back(LaneTableRow{"LN-342", "OKC", "PHX", "intermodal", 1, 9500, 1350, false});
  out->push_back(LaneTableRow{"LN-343", "HOU", "BOS", "flatbed", 2, 11000, 1395, true});
  out->push_back(LaneTableRow{"LN-344", "BOS", "DFW", "flatbed", 3, 12500, 1440, false});
  out->push_back(LaneTableRow{"LN-345", "LAX", "BOS", "reefer", 4, 14000, 1485, false});
  out->push_back(LaneTableRow{"LN-346", "YYZ", "BOS", "flatbed", 5, 15500, 1530, false});
  out->push_back(LaneTableRow{"LN-347", "DEN", "ATL", "reefer", 6, 17000, 1575, false});
  out->push_back(LaneTableRow{"LN-348", "PHX", "YVR", "expedite", 1, 18500, 1620, false});
  out->push_back(LaneTableRow{"LN-349", "SEA", "KCK", "standard", 2, 20000, 1665, false});
  out->push_back(LaneTableRow{"LN-350", "YVR", "OKC", "reefer", 3, 21500, 1710, true});
  out->push_back(LaneTableRow{"LN-351", "DFW", "HOU", "expedite", 4, 23000, 1755, false});
  out->push_back(LaneTableRow{"LN-352", "OKC", "MEM", "intermodal", 5, 8000, 1800, false});
  out->push_back(LaneTableRow{"LN-353", "SLC", "MEM", "intermodal", 6, 9500, 1845, false});
  out->push_back(LaneTableRow{"LN-354", "YYZ", "MSP", "reefer", 1, 11000, 1890, false});
  out->push_back(LaneTableRow{"LN-355", "OKC", "PDX", "reefer", 2, 12500, 1935, false});
  out->push_back(LaneTableRow{"LN-356", "IND", "NSH", "standard", 3, 14000, 1980, false});
  out->push_back(LaneTableRow{"LN-357", "CHI", "ATL", "flatbed", 4, 15500, 2025, true});
  out->push_back(LaneTableRow{"LN-358", "TPA", "PHX", "intermodal", 5, 17000, 2070, false});
  out->push_back(LaneTableRow{"LN-359", "MEM", "SLC", "flatbed", 6, 18500, 2115, false});
}

}  // namespace freight
