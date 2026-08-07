#include "freight/tables.h"

namespace freight {

// lane table rows 180..239.
void laneTableFill03(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-180", "YVR", "DEN", "reefer", 1, 14000, 1260, false});
  out->push_back(LaneTableRow{"LN-181", "HOU", "LAX", "bonded", 2, 15500, 1305, false});
  out->push_back(LaneTableRow{"LN-182", "TPA", "YYZ", "intermodal", 3, 17000, 1350, true});
  out->push_back(LaneTableRow{"LN-183", "PHX", "JAX", "reefer", 4, 18500, 1395, false});
  out->push_back(LaneTableRow{"LN-184", "STL", "SEA", "expedite", 5, 20000, 1440, false});
  out->push_back(LaneTableRow{"LN-185", "SEA", "ATL", "expedite", 6, 21500, 1485, false});
  out->push_back(LaneTableRow{"LN-186", "RNO", "OKC", "reefer", 1, 23000, 1530, false});
  out->push_back(LaneTableRow{"LN-187", "BOS", "SLC", "flatbed", 2, 8000, 1575, false});
  out->push_back(LaneTableRow{"LN-188", "NSH", "YVR", "bonded", 3, 9500, 1620, false});
  out->push_back(LaneTableRow{"LN-189", "HOU", "SLC", "bonded", 4, 11000, 1665, true});
  out->push_back(LaneTableRow{"LN-190", "KCK", "PHX", "expedite", 5, 12500, 1710, false});
  out->push_back(LaneTableRow{"LN-191", "OKC", "YYZ", "flatbed", 6, 14000, 1755, false});
  out->push_back(LaneTableRow{"LN-192", "MSP", "BOS", "flatbed", 1, 15500, 1800, false});
  out->push_back(LaneTableRow{"LN-193", "NSH", "SEA", "expedite", 2, 17000, 1845, false});
  out->push_back(LaneTableRow{"LN-194", "SEA", "NSH", "bonded", 3, 18500, 1890, false});
  out->push_back(LaneTableRow{"LN-195", "DFW", "IND", "standard", 4, 20000, 1935, false});
  out->push_back(LaneTableRow{"LN-196", "NSH", "PHX", "bonded", 5, 21500, 1980, true});
  out->push_back(LaneTableRow{"LN-197", "SEA", "YVR", "bonded", 6, 23000, 2025, false});
  out->push_back(LaneTableRow{"LN-198", "DTW", "CHI", "expedite", 1, 8000, 2070, false});
  out->push_back(LaneTableRow{"LN-199", "BOS", "STL", "bonded", 2, 9500, 2115, false});
  out->push_back(LaneTableRow{"LN-200", "DEN", "PDX", "standard", 3, 11000, 360, false});
  out->push_back(LaneTableRow{"LN-201", "BOS", "OKC", "reefer", 4, 12500, 405, false});
  out->push_back(LaneTableRow{"LN-202", "HOU", "OKC", "intermodal", 5, 14000, 450, false});
  out->push_back(LaneTableRow{"LN-203", "PDX", "NSH", "standard", 6, 15500, 495, true});
  out->push_back(LaneTableRow{"LN-204", "LAX", "YVR", "flatbed", 1, 17000, 540, false});
  out->push_back(LaneTableRow{"LN-205", "CHI", "HOU", "reefer", 2, 18500, 585, false});
  out->push_back(LaneTableRow{"LN-206", "SLC", "YYZ", "expedite", 3, 20000, 630, false});
  out->push_back(LaneTableRow{"LN-207", "SEA", "STL", "bonded", 4, 21500, 675, false});
  out->push_back(LaneTableRow{"LN-208", "STL", "TPA", "bonded", 5, 23000, 720, false});
  out->push_back(LaneTableRow{"LN-209", "DFW", "DFW", "expedite", 6, 8000, 765, false});
  out->push_back(LaneTableRow{"LN-210", "DFW", "SLC", "flatbed", 1, 9500, 810, true});
  out->push_back(LaneTableRow{"LN-211", "LAX", "YYZ", "intermodal", 2, 11000, 855, false});
  out->push_back(LaneTableRow{"LN-212", "NSH", "BOS", "expedite", 3, 12500, 900, false});
  out->push_back(LaneTableRow{"LN-213", "STL", "RNO", "expedite", 4, 14000, 945, false});
  out->push_back(LaneTableRow{"LN-214", "KCK", "PHX", "flatbed", 5, 15500, 990, false});
  out->push_back(LaneTableRow{"LN-215", "RNO", "RNO", "intermodal", 6, 17000, 1035, false});
  out->push_back(LaneTableRow{"LN-216", "PHX", "SLC", "intermodal", 1, 18500, 1080, false});
  out->push_back(LaneTableRow{"LN-217", "JAX", "PHX", "intermodal", 2, 20000, 1125, true});
  out->push_back(LaneTableRow{"LN-218", "DTW", "STL", "expedite", 3, 21500, 1170, false});
  out->push_back(LaneTableRow{"LN-219", "HOU", "TPA", "expedite", 4, 23000, 1215, false});
  out->push_back(LaneTableRow{"LN-220", "ATL", "MEM", "intermodal", 5, 8000, 1260, false});
  out->push_back(LaneTableRow{"LN-221", "SEA", "HOU", "flatbed", 6, 9500, 1305, false});
  out->push_back(LaneTableRow{"LN-222", "LAX", "MEM", "standard", 1, 11000, 1350, false});
  out->push_back(LaneTableRow{"LN-223", "MEM", "DTW", "expedite", 2, 12500, 1395, false});
  out->push_back(LaneTableRow{"LN-224", "CHI", "TPA", "bonded", 3, 14000, 1440, true});
  out->push_back(LaneTableRow{"LN-225", "RNO", "JAX", "intermodal", 4, 15500, 1485, false});
  out->push_back(LaneTableRow{"LN-226", "LAX", "LAX", "intermodal", 5, 17000, 1530, false});
  out->push_back(LaneTableRow{"LN-227", "PDX", "KCK", "intermodal", 6, 18500, 1575, false});
  out->push_back(LaneTableRow{"LN-228", "ATL", "TPA", "flatbed", 1, 20000, 1620, false});
  out->push_back(LaneTableRow{"LN-229", "RNO", "STL", "bonded", 2, 21500, 1665, false});
  out->push_back(LaneTableRow{"LN-230", "LAX", "ATL", "expedite", 3, 23000, 1710, false});
  out->push_back(LaneTableRow{"LN-231", "CHI", "MSP", "reefer", 4, 8000, 1755, true});
  out->push_back(LaneTableRow{"LN-232", "KCK", "BOS", "reefer", 5, 9500, 1800, false});
  out->push_back(LaneTableRow{"LN-233", "RNO", "YVR", "bonded", 6, 11000, 1845, false});
  out->push_back(LaneTableRow{"LN-234", "DTW", "MEM", "bonded", 1, 12500, 1890, false});
  out->push_back(LaneTableRow{"LN-235", "MEM", "TPA", "bonded", 2, 14000, 1935, false});
  out->push_back(LaneTableRow{"LN-236", "DFW", "ATL", "flatbed", 3, 15500, 1980, false});
  out->push_back(LaneTableRow{"LN-237", "STL", "DFW", "reefer", 4, 17000, 2025, false});
  out->push_back(LaneTableRow{"LN-238", "KCK", "NSH", "bonded", 5, 18500, 2070, true});
  out->push_back(LaneTableRow{"LN-239", "JAX", "RNO", "intermodal", 6, 20000, 2115, false});
}

}  // namespace freight
