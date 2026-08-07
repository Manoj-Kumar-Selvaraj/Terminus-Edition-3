#include "freight/tables.h"

namespace freight {

// lane table rows 120..179.
void laneTableFill02(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-120", "NSH", "MEM", "standard", 1, 23000, 360, false});
  out->push_back(LaneTableRow{"LN-121", "MEM", "YYZ", "bonded", 2, 8000, 405, false});
  out->push_back(LaneTableRow{"LN-122", "SLC", "RNO", "intermodal", 3, 9500, 450, false});
  out->push_back(LaneTableRow{"LN-123", "PDX", "STL", "intermodal", 4, 11000, 495, false});
  out->push_back(LaneTableRow{"LN-124", "PHX", "YYZ", "bonded", 5, 12500, 540, false});
  out->push_back(LaneTableRow{"LN-125", "DFW", "SLC", "flatbed", 6, 14000, 585, false});
  out->push_back(LaneTableRow{"LN-126", "DTW", "IND", "expedite", 1, 15500, 630, true});
  out->push_back(LaneTableRow{"LN-127", "JAX", "BOS", "flatbed", 2, 17000, 675, false});
  out->push_back(LaneTableRow{"LN-128", "YYZ", "DTW", "reefer", 3, 18500, 720, false});
  out->push_back(LaneTableRow{"LN-129", "DFW", "TPA", "bonded", 4, 20000, 765, false});
  out->push_back(LaneTableRow{"LN-130", "OKC", "STL", "bonded", 5, 21500, 810, false});
  out->push_back(LaneTableRow{"LN-131", "YVR", "YYZ", "flatbed", 6, 23000, 855, false});
  out->push_back(LaneTableRow{"LN-132", "BOS", "IND", "reefer", 1, 8000, 900, false});
  out->push_back(LaneTableRow{"LN-133", "JAX", "DEN", "standard", 2, 9500, 945, true});
  out->push_back(LaneTableRow{"LN-134", "DFW", "NSH", "bonded", 3, 11000, 990, false});
  out->push_back(LaneTableRow{"LN-135", "HOU", "PDX", "bonded", 4, 12500, 1035, false});
  out->push_back(LaneTableRow{"LN-136", "IND", "DFW", "standard", 5, 14000, 1080, false});
  out->push_back(LaneTableRow{"LN-137", "JAX", "STL", "bonded", 6, 15500, 1125, false});
  out->push_back(LaneTableRow{"LN-138", "DFW", "BOS", "flatbed", 1, 17000, 1170, false});
  out->push_back(LaneTableRow{"LN-139", "TPA", "MSP", "intermodal", 2, 18500, 1215, false});
  out->push_back(LaneTableRow{"LN-140", "BOS", "TPA", "flatbed", 3, 20000, 1260, true});
  out->push_back(LaneTableRow{"LN-141", "RNO", "DTW", "flatbed", 4, 21500, 1305, false});
  out->push_back(LaneTableRow{"LN-142", "PHX", "JAX", "intermodal", 5, 23000, 1350, false});
  out->push_back(LaneTableRow{"LN-143", "MSP", "YYZ", "expedite", 6, 8000, 1395, false});
  out->push_back(LaneTableRow{"LN-144", "SEA", "STL", "bonded", 1, 9500, 1440, false});
  out->push_back(LaneTableRow{"LN-145", "PHX", "CHI", "reefer", 2, 11000, 1485, false});
  out->push_back(LaneTableRow{"LN-146", "STL", "STL", "bonded", 3, 12500, 1530, false});
  out->push_back(LaneTableRow{"LN-147", "MEM", "NSH", "intermodal", 4, 14000, 1575, true});
  out->push_back(LaneTableRow{"LN-148", "NSH", "DEN", "flatbed", 5, 15500, 1620, false});
  out->push_back(LaneTableRow{"LN-149", "BOS", "PHX", "intermodal", 6, 17000, 1665, false});
  out->push_back(LaneTableRow{"LN-150", "PDX", "SEA", "flatbed", 1, 18500, 1710, false});
  out->push_back(LaneTableRow{"LN-151", "MEM", "SEA", "expedite", 2, 20000, 1755, false});
  out->push_back(LaneTableRow{"LN-152", "MSP", "PHX", "bonded", 3, 21500, 1800, false});
  out->push_back(LaneTableRow{"LN-153", "DTW", "STL", "bonded", 4, 23000, 1845, false});
  out->push_back(LaneTableRow{"LN-154", "NSH", "ATL", "standard", 5, 8000, 1890, true});
  out->push_back(LaneTableRow{"LN-155", "YYZ", "OKC", "standard", 6, 9500, 1935, false});
  out->push_back(LaneTableRow{"LN-156", "YVR", "PHX", "flatbed", 1, 11000, 1980, false});
  out->push_back(LaneTableRow{"LN-157", "JAX", "MSP", "reefer", 2, 12500, 2025, false});
  out->push_back(LaneTableRow{"LN-158", "DTW", "NSH", "bonded", 3, 14000, 2070, false});
  out->push_back(LaneTableRow{"LN-159", "ATL", "TPA", "expedite", 4, 15500, 2115, false});
  out->push_back(LaneTableRow{"LN-160", "SEA", "IND", "flatbed", 5, 17000, 360, false});
  out->push_back(LaneTableRow{"LN-161", "DTW", "SLC", "intermodal", 6, 18500, 405, true});
  out->push_back(LaneTableRow{"LN-162", "SEA", "ATL", "flatbed", 1, 20000, 450, false});
  out->push_back(LaneTableRow{"LN-163", "TPA", "TPA", "intermodal", 2, 21500, 495, false});
  out->push_back(LaneTableRow{"LN-164", "TPA", "JAX", "intermodal", 3, 23000, 540, false});
  out->push_back(LaneTableRow{"LN-165", "CHI", "JAX", "standard", 4, 8000, 585, false});
  out->push_back(LaneTableRow{"LN-166", "KCK", "SEA", "flatbed", 5, 9500, 630, false});
  out->push_back(LaneTableRow{"LN-167", "IND", "KCK", "bonded", 6, 11000, 675, false});
  out->push_back(LaneTableRow{"LN-168", "MEM", "CHI", "standard", 1, 12500, 720, true});
  out->push_back(LaneTableRow{"LN-169", "BOS", "ATL", "expedite", 2, 14000, 765, false});
  out->push_back(LaneTableRow{"LN-170", "BOS", "IND", "flatbed", 3, 15500, 810, false});
  out->push_back(LaneTableRow{"LN-171", "NSH", "IND", "flatbed", 4, 17000, 855, false});
  out->push_back(LaneTableRow{"LN-172", "DEN", "MSP", "bonded", 5, 18500, 900, false});
  out->push_back(LaneTableRow{"LN-173", "CHI", "IND", "flatbed", 6, 20000, 945, false});
  out->push_back(LaneTableRow{"LN-174", "BOS", "MSP", "standard", 1, 21500, 990, false});
  out->push_back(LaneTableRow{"LN-175", "YYZ", "DFW", "expedite", 2, 23000, 1035, true});
  out->push_back(LaneTableRow{"LN-176", "OKC", "IND", "standard", 3, 8000, 1080, false});
  out->push_back(LaneTableRow{"LN-177", "STL", "MSP", "standard", 4, 9500, 1125, false});
  out->push_back(LaneTableRow{"LN-178", "DFW", "STL", "flatbed", 5, 11000, 1170, false});
  out->push_back(LaneTableRow{"LN-179", "SLC", "YYZ", "bonded", 6, 12500, 1215, false});
}

}  // namespace freight
