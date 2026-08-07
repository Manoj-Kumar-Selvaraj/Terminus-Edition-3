#include "freight/tables.h"

namespace freight {

// lane table rows 360..419.
void laneTableFill06(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-360", "DEN", "BOS", "expedite", 1, 20000, 360, false});
  out->push_back(LaneTableRow{"LN-361", "OKC", "SEA", "flatbed", 2, 21500, 405, false});
  out->push_back(LaneTableRow{"LN-362", "CHI", "SLC", "expedite", 3, 23000, 450, false});
  out->push_back(LaneTableRow{"LN-363", "YVR", "RNO", "intermodal", 4, 8000, 495, false});
  out->push_back(LaneTableRow{"LN-364", "IND", "IND", "reefer", 5, 9500, 540, true});
  out->push_back(LaneTableRow{"LN-365", "LAX", "PHX", "intermodal", 6, 11000, 585, false});
  out->push_back(LaneTableRow{"LN-366", "BOS", "DFW", "reefer", 1, 12500, 630, false});
  out->push_back(LaneTableRow{"LN-367", "SLC", "BOS", "standard", 2, 14000, 675, false});
  out->push_back(LaneTableRow{"LN-368", "MSP", "HOU", "reefer", 3, 15500, 720, false});
  out->push_back(LaneTableRow{"LN-369", "YVR", "BOS", "standard", 4, 17000, 765, false});
  out->push_back(LaneTableRow{"LN-370", "ATL", "NSH", "bonded", 5, 18500, 810, false});
  out->push_back(LaneTableRow{"LN-371", "ATL", "DFW", "flatbed", 6, 20000, 855, true});
  out->push_back(LaneTableRow{"LN-372", "DTW", "MEM", "intermodal", 1, 21500, 900, false});
  out->push_back(LaneTableRow{"LN-373", "HOU", "PDX", "intermodal", 2, 23000, 945, false});
  out->push_back(LaneTableRow{"LN-374", "KCK", "RNO", "expedite", 3, 8000, 990, false});
  out->push_back(LaneTableRow{"LN-375", "CHI", "OKC", "standard", 4, 9500, 1035, false});
  out->push_back(LaneTableRow{"LN-376", "TPA", "DFW", "expedite", 5, 11000, 1080, false});
  out->push_back(LaneTableRow{"LN-377", "DFW", "DEN", "reefer", 6, 12500, 1125, false});
  out->push_back(LaneTableRow{"LN-378", "YVR", "MSP", "bonded", 1, 14000, 1170, true});
  out->push_back(LaneTableRow{"LN-379", "MEM", "OKC", "intermodal", 2, 15500, 1215, false});
  out->push_back(LaneTableRow{"LN-380", "HOU", "MEM", "reefer", 3, 17000, 1260, false});
  out->push_back(LaneTableRow{"LN-381", "YYZ", "KCK", "reefer", 4, 18500, 1305, false});
  out->push_back(LaneTableRow{"LN-382", "YYZ", "PHX", "expedite", 5, 20000, 1350, false});
  out->push_back(LaneTableRow{"LN-383", "STL", "MSP", "intermodal", 6, 21500, 1395, false});
  out->push_back(LaneTableRow{"LN-384", "TPA", "MSP", "bonded", 1, 23000, 1440, false});
  out->push_back(LaneTableRow{"LN-385", "LAX", "PHX", "bonded", 2, 8000, 1485, true});
  out->push_back(LaneTableRow{"LN-386", "IND", "RNO", "expedite", 3, 9500, 1530, false});
  out->push_back(LaneTableRow{"LN-387", "CHI", "TPA", "expedite", 4, 11000, 1575, false});
  out->push_back(LaneTableRow{"LN-388", "PDX", "BOS", "standard", 5, 12500, 1620, false});
  out->push_back(LaneTableRow{"LN-389", "JAX", "BOS", "flatbed", 6, 14000, 1665, false});
  out->push_back(LaneTableRow{"LN-390", "YYZ", "OKC", "standard", 1, 15500, 1710, false});
  out->push_back(LaneTableRow{"LN-391", "BOS", "YVR", "intermodal", 2, 17000, 1755, false});
  out->push_back(LaneTableRow{"LN-392", "NSH", "IND", "flatbed", 3, 18500, 1800, true});
  out->push_back(LaneTableRow{"LN-393", "KCK", "PHX", "bonded", 4, 20000, 1845, false});
  out->push_back(LaneTableRow{"LN-394", "PDX", "DFW", "expedite", 5, 21500, 1890, false});
  out->push_back(LaneTableRow{"LN-395", "PHX", "OKC", "intermodal", 6, 23000, 1935, false});
  out->push_back(LaneTableRow{"LN-396", "JAX", "DFW", "expedite", 1, 8000, 1980, false});
  out->push_back(LaneTableRow{"LN-397", "CHI", "SLC", "bonded", 2, 9500, 2025, false});
  out->push_back(LaneTableRow{"LN-398", "CHI", "ATL", "reefer", 3, 11000, 2070, false});
  out->push_back(LaneTableRow{"LN-399", "LAX", "IND", "flatbed", 4, 12500, 2115, true});
  out->push_back(LaneTableRow{"LN-400", "JAX", "DEN", "flatbed", 5, 14000, 360, false});
  out->push_back(LaneTableRow{"LN-401", "OKC", "MEM", "reefer", 6, 15500, 405, false});
  out->push_back(LaneTableRow{"LN-402", "DEN", "OKC", "reefer", 1, 17000, 450, false});
  out->push_back(LaneTableRow{"LN-403", "JAX", "NSH", "intermodal", 2, 18500, 495, false});
  out->push_back(LaneTableRow{"LN-404", "JAX", "NSH", "bonded", 3, 20000, 540, false});
  out->push_back(LaneTableRow{"LN-405", "SLC", "DTW", "flatbed", 4, 21500, 585, false});
  out->push_back(LaneTableRow{"LN-406", "PDX", "TPA", "intermodal", 5, 23000, 630, true});
  out->push_back(LaneTableRow{"LN-407", "STL", "YVR", "bonded", 6, 8000, 675, false});
  out->push_back(LaneTableRow{"LN-408", "SEA", "SLC", "flatbed", 1, 9500, 720, false});
  out->push_back(LaneTableRow{"LN-409", "PHX", "YVR", "bonded", 2, 11000, 765, false});
  out->push_back(LaneTableRow{"LN-410", "SLC", "MSP", "intermodal", 3, 12500, 810, false});
  out->push_back(LaneTableRow{"LN-411", "DFW", "HOU", "flatbed", 4, 14000, 855, false});
  out->push_back(LaneTableRow{"LN-412", "ATL", "NSH", "reefer", 5, 15500, 900, false});
  out->push_back(LaneTableRow{"LN-413", "JAX", "SEA", "flatbed", 6, 17000, 945, true});
  out->push_back(LaneTableRow{"LN-414", "KCK", "BOS", "reefer", 1, 18500, 990, false});
  out->push_back(LaneTableRow{"LN-415", "JAX", "BOS", "expedite", 2, 20000, 1035, false});
  out->push_back(LaneTableRow{"LN-416", "TPA", "DTW", "reefer", 3, 21500, 1080, false});
  out->push_back(LaneTableRow{"LN-417", "STL", "KCK", "reefer", 4, 23000, 1125, false});
  out->push_back(LaneTableRow{"LN-418", "NSH", "PHX", "expedite", 5, 8000, 1170, false});
  out->push_back(LaneTableRow{"LN-419", "PHX", "SLC", "intermodal", 6, 9500, 1215, false});
}

}  // namespace freight
