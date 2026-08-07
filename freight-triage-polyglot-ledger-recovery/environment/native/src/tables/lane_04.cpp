#include "freight/tables.h"

namespace freight {

// lane table rows 240..299.
void laneTableFill04(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-240", "RNO", "OKC", "bonded", 1, 21500, 360, false});
  out->push_back(LaneTableRow{"LN-241", "OKC", "KCK", "bonded", 2, 23000, 405, false});
  out->push_back(LaneTableRow{"LN-242", "NSH", "JAX", "standard", 3, 8000, 450, false});
  out->push_back(LaneTableRow{"LN-243", "JAX", "PHX", "intermodal", 4, 9500, 495, false});
  out->push_back(LaneTableRow{"LN-244", "CHI", "DTW", "flatbed", 5, 11000, 540, false});
  out->push_back(LaneTableRow{"LN-245", "SEA", "MSP", "standard", 6, 12500, 585, true});
  out->push_back(LaneTableRow{"LN-246", "CHI", "HOU", "flatbed", 1, 14000, 630, false});
  out->push_back(LaneTableRow{"LN-247", "PDX", "IND", "reefer", 2, 15500, 675, false});
  out->push_back(LaneTableRow{"LN-248", "BOS", "PDX", "standard", 3, 17000, 720, false});
  out->push_back(LaneTableRow{"LN-249", "SEA", "NSH", "intermodal", 4, 18500, 765, false});
  out->push_back(LaneTableRow{"LN-250", "DTW", "SEA", "bonded", 5, 20000, 810, false});
  out->push_back(LaneTableRow{"LN-251", "ATL", "TPA", "intermodal", 6, 21500, 855, false});
  out->push_back(LaneTableRow{"LN-252", "OKC", "MSP", "bonded", 1, 23000, 900, true});
  out->push_back(LaneTableRow{"LN-253", "DTW", "PDX", "standard", 2, 8000, 945, false});
  out->push_back(LaneTableRow{"LN-254", "MSP", "PHX", "intermodal", 3, 9500, 990, false});
  out->push_back(LaneTableRow{"LN-255", "CHI", "SLC", "expedite", 4, 11000, 1035, false});
  out->push_back(LaneTableRow{"LN-256", "IND", "HOU", "flatbed", 5, 12500, 1080, false});
  out->push_back(LaneTableRow{"LN-257", "CHI", "TPA", "expedite", 6, 14000, 1125, false});
  out->push_back(LaneTableRow{"LN-258", "YYZ", "MSP", "intermodal", 1, 15500, 1170, false});
  out->push_back(LaneTableRow{"LN-259", "CHI", "PDX", "reefer", 2, 17000, 1215, true});
  out->push_back(LaneTableRow{"LN-260", "ATL", "YVR", "intermodal", 3, 18500, 1260, false});
  out->push_back(LaneTableRow{"LN-261", "ATL", "CHI", "expedite", 4, 20000, 1305, false});
  out->push_back(LaneTableRow{"LN-262", "NSH", "YVR", "expedite", 5, 21500, 1350, false});
  out->push_back(LaneTableRow{"LN-263", "MSP", "YYZ", "bonded", 6, 23000, 1395, false});
  out->push_back(LaneTableRow{"LN-264", "DEN", "HOU", "expedite", 1, 8000, 1440, false});
  out->push_back(LaneTableRow{"LN-265", "OKC", "MSP", "standard", 2, 9500, 1485, false});
  out->push_back(LaneTableRow{"LN-266", "MEM", "JAX", "reefer", 3, 11000, 1530, true});
  out->push_back(LaneTableRow{"LN-267", "SEA", "DFW", "standard", 4, 12500, 1575, false});
  out->push_back(LaneTableRow{"LN-268", "JAX", "RNO", "flatbed", 5, 14000, 1620, false});
  out->push_back(LaneTableRow{"LN-269", "STL", "MEM", "reefer", 6, 15500, 1665, false});
  out->push_back(LaneTableRow{"LN-270", "HOU", "YVR", "expedite", 1, 17000, 1710, false});
  out->push_back(LaneTableRow{"LN-271", "ATL", "HOU", "expedite", 2, 18500, 1755, false});
  out->push_back(LaneTableRow{"LN-272", "MSP", "OKC", "intermodal", 3, 20000, 1800, false});
  out->push_back(LaneTableRow{"LN-273", "JAX", "MEM", "reefer", 4, 21500, 1845, true});
  out->push_back(LaneTableRow{"LN-274", "PHX", "YVR", "flatbed", 5, 23000, 1890, false});
  out->push_back(LaneTableRow{"LN-275", "SEA", "YYZ", "flatbed", 6, 8000, 1935, false});
  out->push_back(LaneTableRow{"LN-276", "MSP", "HOU", "reefer", 1, 9500, 1980, false});
  out->push_back(LaneTableRow{"LN-277", "STL", "DFW", "standard", 2, 11000, 2025, false});
  out->push_back(LaneTableRow{"LN-278", "HOU", "SLC", "intermodal", 3, 12500, 2070, false});
  out->push_back(LaneTableRow{"LN-279", "STL", "JAX", "intermodal", 4, 14000, 2115, false});
  out->push_back(LaneTableRow{"LN-280", "HOU", "YYZ", "flatbed", 5, 15500, 360, true});
  out->push_back(LaneTableRow{"LN-281", "HOU", "STL", "intermodal", 6, 17000, 405, false});
  out->push_back(LaneTableRow{"LN-282", "SLC", "IND", "flatbed", 1, 18500, 450, false});
  out->push_back(LaneTableRow{"LN-283", "HOU", "KCK", "reefer", 2, 20000, 495, false});
  out->push_back(LaneTableRow{"LN-284", "SLC", "STL", "bonded", 3, 21500, 540, false});
  out->push_back(LaneTableRow{"LN-285", "STL", "MEM", "intermodal", 4, 23000, 585, false});
  out->push_back(LaneTableRow{"LN-286", "BOS", "HOU", "expedite", 5, 8000, 630, false});
  out->push_back(LaneTableRow{"LN-287", "SLC", "DTW", "standard", 6, 9500, 675, true});
  out->push_back(LaneTableRow{"LN-288", "RNO", "DTW", "reefer", 1, 11000, 720, false});
  out->push_back(LaneTableRow{"LN-289", "SEA", "MEM", "reefer", 2, 12500, 765, false});
  out->push_back(LaneTableRow{"LN-290", "JAX", "MSP", "reefer", 3, 14000, 810, false});
  out->push_back(LaneTableRow{"LN-291", "YYZ", "STL", "expedite", 4, 15500, 855, false});
  out->push_back(LaneTableRow{"LN-292", "YYZ", "SEA", "flatbed", 5, 17000, 900, false});
  out->push_back(LaneTableRow{"LN-293", "STL", "KCK", "reefer", 6, 18500, 945, false});
  out->push_back(LaneTableRow{"LN-294", "IND", "JAX", "bonded", 1, 20000, 990, true});
  out->push_back(LaneTableRow{"LN-295", "SLC", "DEN", "standard", 2, 21500, 1035, false});
  out->push_back(LaneTableRow{"LN-296", "DEN", "ATL", "expedite", 3, 23000, 1080, false});
  out->push_back(LaneTableRow{"LN-297", "SEA", "CHI", "expedite", 4, 8000, 1125, false});
  out->push_back(LaneTableRow{"LN-298", "HOU", "MSP", "bonded", 5, 9500, 1170, false});
  out->push_back(LaneTableRow{"LN-299", "BOS", "YYZ", "expedite", 6, 11000, 1215, false});
}

}  // namespace freight
