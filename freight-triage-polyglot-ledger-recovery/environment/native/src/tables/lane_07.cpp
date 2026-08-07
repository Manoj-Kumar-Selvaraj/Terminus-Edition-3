#include "freight/tables.h"

namespace freight {

// lane table rows 420..479.
void laneTableFill07(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-420", "ATL", "MEM", "bonded", 1, 11000, 1260, true});
  out->push_back(LaneTableRow{"LN-421", "DFW", "SEA", "bonded", 2, 12500, 1305, false});
  out->push_back(LaneTableRow{"LN-422", "PHX", "RNO", "bonded", 3, 14000, 1350, false});
  out->push_back(LaneTableRow{"LN-423", "YYZ", "YVR", "expedite", 4, 15500, 1395, false});
  out->push_back(LaneTableRow{"LN-424", "JAX", "PDX", "intermodal", 5, 17000, 1440, false});
  out->push_back(LaneTableRow{"LN-425", "RNO", "YYZ", "flatbed", 6, 18500, 1485, false});
  out->push_back(LaneTableRow{"LN-426", "YVR", "CHI", "reefer", 1, 20000, 1530, false});
  out->push_back(LaneTableRow{"LN-427", "DTW", "YVR", "flatbed", 2, 21500, 1575, true});
  out->push_back(LaneTableRow{"LN-428", "OKC", "NSH", "bonded", 3, 23000, 1620, false});
  out->push_back(LaneTableRow{"LN-429", "IND", "CHI", "expedite", 4, 8000, 1665, false});
  out->push_back(LaneTableRow{"LN-430", "NSH", "DTW", "standard", 5, 9500, 1710, false});
  out->push_back(LaneTableRow{"LN-431", "RNO", "NSH", "standard", 6, 11000, 1755, false});
  out->push_back(LaneTableRow{"LN-432", "SLC", "DEN", "flatbed", 1, 12500, 1800, false});
  out->push_back(LaneTableRow{"LN-433", "IND", "HOU", "expedite", 2, 14000, 1845, false});
  out->push_back(LaneTableRow{"LN-434", "RNO", "MEM", "bonded", 3, 15500, 1890, true});
  out->push_back(LaneTableRow{"LN-435", "DTW", "PHX", "expedite", 4, 17000, 1935, false});
  out->push_back(LaneTableRow{"LN-436", "YYZ", "DTW", "reefer", 5, 18500, 1980, false});
  out->push_back(LaneTableRow{"LN-437", "PHX", "OKC", "intermodal", 6, 20000, 2025, false});
  out->push_back(LaneTableRow{"LN-438", "SEA", "HOU", "flatbed", 1, 21500, 2070, false});
  out->push_back(LaneTableRow{"LN-439", "LAX", "KCK", "reefer", 2, 23000, 2115, false});
  out->push_back(LaneTableRow{"LN-440", "PHX", "LAX", "intermodal", 3, 8000, 360, false});
  out->push_back(LaneTableRow{"LN-441", "DEN", "CHI", "expedite", 4, 9500, 405, true});
  out->push_back(LaneTableRow{"LN-442", "HOU", "SLC", "flatbed", 5, 11000, 450, false});
  out->push_back(LaneTableRow{"LN-443", "IND", "PDX", "standard", 6, 12500, 495, false});
  out->push_back(LaneTableRow{"LN-444", "SLC", "SLC", "flatbed", 1, 14000, 540, false});
  out->push_back(LaneTableRow{"LN-445", "DEN", "TPA", "flatbed", 2, 15500, 585, false});
  out->push_back(LaneTableRow{"LN-446", "LAX", "DTW", "expedite", 3, 17000, 630, false});
  out->push_back(LaneTableRow{"LN-447", "MSP", "KCK", "standard", 4, 18500, 675, false});
  out->push_back(LaneTableRow{"LN-448", "RNO", "HOU", "standard", 5, 20000, 720, true});
  out->push_back(LaneTableRow{"LN-449", "DEN", "YVR", "bonded", 6, 21500, 765, false});
  out->push_back(LaneTableRow{"LN-450", "MEM", "NSH", "standard", 1, 23000, 810, false});
  out->push_back(LaneTableRow{"LN-451", "PHX", "DTW", "reefer", 2, 8000, 855, false});
  out->push_back(LaneTableRow{"LN-452", "STL", "OKC", "standard", 3, 9500, 900, false});
  out->push_back(LaneTableRow{"LN-453", "NSH", "NSH", "intermodal", 4, 11000, 945, false});
  out->push_back(LaneTableRow{"LN-454", "CHI", "PHX", "flatbed", 5, 12500, 990, false});
  out->push_back(LaneTableRow{"LN-455", "DTW", "SLC", "expedite", 6, 14000, 1035, true});
  out->push_back(LaneTableRow{"LN-456", "BOS", "ATL", "reefer", 1, 15500, 1080, false});
  out->push_back(LaneTableRow{"LN-457", "DTW", "KCK", "standard", 2, 17000, 1125, false});
  out->push_back(LaneTableRow{"LN-458", "CHI", "TPA", "flatbed", 3, 18500, 1170, false});
  out->push_back(LaneTableRow{"LN-459", "MEM", "IND", "flatbed", 4, 20000, 1215, false});
  out->push_back(LaneTableRow{"LN-460", "JAX", "BOS", "standard", 5, 21500, 1260, false});
  out->push_back(LaneTableRow{"LN-461", "IND", "DTW", "reefer", 6, 23000, 1305, false});
  out->push_back(LaneTableRow{"LN-462", "MSP", "STL", "intermodal", 1, 8000, 1350, true});
  out->push_back(LaneTableRow{"LN-463", "SEA", "CHI", "standard", 2, 9500, 1395, false});
  out->push_back(LaneTableRow{"LN-464", "YVR", "STL", "intermodal", 3, 11000, 1440, false});
  out->push_back(LaneTableRow{"LN-465", "YYZ", "OKC", "bonded", 4, 12500, 1485, false});
  out->push_back(LaneTableRow{"LN-466", "JAX", "YVR", "flatbed", 5, 14000, 1530, false});
  out->push_back(LaneTableRow{"LN-467", "SEA", "CHI", "standard", 6, 15500, 1575, false});
  out->push_back(LaneTableRow{"LN-468", "NSH", "YVR", "expedite", 1, 17000, 1620, false});
  out->push_back(LaneTableRow{"LN-469", "MSP", "LAX", "standard", 2, 18500, 1665, true});
  out->push_back(LaneTableRow{"LN-470", "KCK", "SEA", "flatbed", 3, 20000, 1710, false});
  out->push_back(LaneTableRow{"LN-471", "YYZ", "TPA", "intermodal", 4, 21500, 1755, false});
  out->push_back(LaneTableRow{"LN-472", "STL", "SEA", "expedite", 5, 23000, 1800, false});
  out->push_back(LaneTableRow{"LN-473", "STL", "TPA", "expedite", 6, 8000, 1845, false});
  out->push_back(LaneTableRow{"LN-474", "KCK", "BOS", "standard", 1, 9500, 1890, false});
  out->push_back(LaneTableRow{"LN-475", "IND", "BOS", "flatbed", 2, 11000, 1935, false});
  out->push_back(LaneTableRow{"LN-476", "PHX", "YYZ", "flatbed", 3, 12500, 1980, true});
  out->push_back(LaneTableRow{"LN-477", "NSH", "NSH", "standard", 4, 14000, 2025, false});
  out->push_back(LaneTableRow{"LN-478", "CHI", "SLC", "expedite", 5, 15500, 2070, false});
  out->push_back(LaneTableRow{"LN-479", "STL", "DTW", "standard", 6, 17000, 2115, false});
}

}  // namespace freight
