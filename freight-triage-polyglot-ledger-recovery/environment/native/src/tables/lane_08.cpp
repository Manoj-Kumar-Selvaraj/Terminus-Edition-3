#include "freight/tables.h"

namespace freight {

// lane table rows 480..519.
void laneTableFill08(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-480", "DTW", "PDX", "standard", 1, 18500, 360, false});
  out->push_back(LaneTableRow{"LN-481", "BOS", "KCK", "reefer", 2, 20000, 405, false});
  out->push_back(LaneTableRow{"LN-482", "PHX", "YYZ", "intermodal", 3, 21500, 450, false});
  out->push_back(LaneTableRow{"LN-483", "SEA", "YVR", "expedite", 4, 23000, 495, true});
  out->push_back(LaneTableRow{"LN-484", "KCK", "IND", "expedite", 5, 8000, 540, false});
  out->push_back(LaneTableRow{"LN-485", "JAX", "LAX", "reefer", 6, 9500, 585, false});
  out->push_back(LaneTableRow{"LN-486", "BOS", "PHX", "intermodal", 1, 11000, 630, false});
  out->push_back(LaneTableRow{"LN-487", "TPA", "OKC", "intermodal", 2, 12500, 675, false});
  out->push_back(LaneTableRow{"LN-488", "DFW", "IND", "expedite", 3, 14000, 720, false});
  out->push_back(LaneTableRow{"LN-489", "RNO", "STL", "expedite", 4, 15500, 765, false});
  out->push_back(LaneTableRow{"LN-490", "STL", "KCK", "reefer", 5, 17000, 810, true});
  out->push_back(LaneTableRow{"LN-491", "KCK", "SEA", "bonded", 6, 18500, 855, false});
  out->push_back(LaneTableRow{"LN-492", "KCK", "PHX", "bonded", 1, 20000, 900, false});
  out->push_back(LaneTableRow{"LN-493", "CHI", "PHX", "intermodal", 2, 21500, 945, false});
  out->push_back(LaneTableRow{"LN-494", "YVR", "NSH", "reefer", 3, 23000, 990, false});
  out->push_back(LaneTableRow{"LN-495", "PHX", "DTW", "reefer", 4, 8000, 1035, false});
  out->push_back(LaneTableRow{"LN-496", "YVR", "PHX", "intermodal", 5, 9500, 1080, false});
  out->push_back(LaneTableRow{"LN-497", "PHX", "LAX", "reefer", 6, 11000, 1125, true});
  out->push_back(LaneTableRow{"LN-498", "JAX", "PDX", "standard", 1, 12500, 1170, false});
  out->push_back(LaneTableRow{"LN-499", "YYZ", "SEA", "flatbed", 2, 14000, 1215, false});
  out->push_back(LaneTableRow{"LN-500", "MSP", "YYZ", "expedite", 3, 15500, 1260, false});
  out->push_back(LaneTableRow{"LN-501", "IND", "SLC", "intermodal", 4, 17000, 1305, false});
  out->push_back(LaneTableRow{"LN-502", "OKC", "PHX", "bonded", 5, 18500, 1350, false});
  out->push_back(LaneTableRow{"LN-503", "LAX", "MSP", "bonded", 6, 20000, 1395, false});
  out->push_back(LaneTableRow{"LN-504", "SEA", "DTW", "expedite", 1, 21500, 1440, true});
  out->push_back(LaneTableRow{"LN-505", "DEN", "STL", "flatbed", 2, 23000, 1485, false});
  out->push_back(LaneTableRow{"LN-506", "BOS", "MSP", "reefer", 3, 8000, 1530, false});
  out->push_back(LaneTableRow{"LN-507", "YYZ", "BOS", "standard", 4, 9500, 1575, false});
  out->push_back(LaneTableRow{"LN-508", "LAX", "KCK", "bonded", 5, 11000, 1620, false});
  out->push_back(LaneTableRow{"LN-509", "YYZ", "CHI", "reefer", 6, 12500, 1665, false});
  out->push_back(LaneTableRow{"LN-510", "KCK", "YVR", "flatbed", 1, 14000, 1710, false});
  out->push_back(LaneTableRow{"LN-511", "DTW", "DEN", "reefer", 2, 15500, 1755, true});
  out->push_back(LaneTableRow{"LN-512", "SEA", "OKC", "intermodal", 3, 17000, 1800, false});
  out->push_back(LaneTableRow{"LN-513", "STL", "MEM", "reefer", 4, 18500, 1845, false});
  out->push_back(LaneTableRow{"LN-514", "CHI", "RNO", "flatbed", 5, 20000, 1890, false});
  out->push_back(LaneTableRow{"LN-515", "RNO", "MSP", "intermodal", 6, 21500, 1935, false});
  out->push_back(LaneTableRow{"LN-516", "LAX", "DEN", "reefer", 1, 23000, 1980, false});
  out->push_back(LaneTableRow{"LN-517", "KCK", "PHX", "flatbed", 2, 8000, 2025, false});
  out->push_back(LaneTableRow{"LN-518", "DFW", "NSH", "standard", 3, 9500, 2070, true});
  out->push_back(LaneTableRow{"LN-519", "YVR", "RNO", "intermodal", 4, 11000, 2115, false});
}

}  // namespace freight
