#include "freight/tables.h"

namespace freight {

// lane table rows 60..119.
void laneTableFill01(std::vector<LaneTableRow>* out) {
  out->push_back(LaneTableRow{"LN-060", "NSH", "KCK", "intermodal", 1, 15500, 1260, false});
  out->push_back(LaneTableRow{"LN-061", "MSP", "NSH", "standard", 2, 17000, 1305, false});
  out->push_back(LaneTableRow{"LN-062", "DTW", "HOU", "flatbed", 3, 18500, 1350, false});
  out->push_back(LaneTableRow{"LN-063", "YYZ", "OKC", "reefer", 4, 20000, 1395, true});
  out->push_back(LaneTableRow{"LN-064", "SEA", "NSH", "reefer", 5, 21500, 1440, false});
  out->push_back(LaneTableRow{"LN-065", "OKC", "BOS", "expedite", 6, 23000, 1485, false});
  out->push_back(LaneTableRow{"LN-066", "LAX", "PHX", "expedite", 1, 8000, 1530, false});
  out->push_back(LaneTableRow{"LN-067", "STL", "HOU", "expedite", 2, 9500, 1575, false});
  out->push_back(LaneTableRow{"LN-068", "MSP", "ATL", "flatbed", 3, 11000, 1620, false});
  out->push_back(LaneTableRow{"LN-069", "CHI", "OKC", "bonded", 4, 12500, 1665, false});
  out->push_back(LaneTableRow{"LN-070", "YVR", "NSH", "bonded", 5, 14000, 1710, true});
  out->push_back(LaneTableRow{"LN-071", "RNO", "DTW", "reefer", 6, 15500, 1755, false});
  out->push_back(LaneTableRow{"LN-072", "CHI", "MEM", "intermodal", 1, 17000, 1800, false});
  out->push_back(LaneTableRow{"LN-073", "STL", "IND", "reefer", 2, 18500, 1845, false});
  out->push_back(LaneTableRow{"LN-074", "HOU", "KCK", "intermodal", 3, 20000, 1890, false});
  out->push_back(LaneTableRow{"LN-075", "DFW", "DFW", "standard", 4, 21500, 1935, false});
  out->push_back(LaneTableRow{"LN-076", "IND", "KCK", "reefer", 5, 23000, 1980, false});
  out->push_back(LaneTableRow{"LN-077", "TPA", "STL", "intermodal", 6, 8000, 2025, true});
  out->push_back(LaneTableRow{"LN-078", "IND", "KCK", "bonded", 1, 9500, 2070, false});
  out->push_back(LaneTableRow{"LN-079", "DEN", "JAX", "bonded", 2, 11000, 2115, false});
  out->push_back(LaneTableRow{"LN-080", "LAX", "PHX", "intermodal", 3, 12500, 360, false});
  out->push_back(LaneTableRow{"LN-081", "CHI", "YVR", "expedite", 4, 14000, 405, false});
  out->push_back(LaneTableRow{"LN-082", "JAX", "NSH", "bonded", 5, 15500, 450, false});
  out->push_back(LaneTableRow{"LN-083", "STL", "YYZ", "expedite", 6, 17000, 495, false});
  out->push_back(LaneTableRow{"LN-084", "LAX", "LAX", "reefer", 1, 18500, 540, true});
  out->push_back(LaneTableRow{"LN-085", "DFW", "HOU", "expedite", 2, 20000, 585, false});
  out->push_back(LaneTableRow{"LN-086", "SLC", "BOS", "standard", 3, 21500, 630, false});
  out->push_back(LaneTableRow{"LN-087", "LAX", "CHI", "expedite", 4, 23000, 675, false});
  out->push_back(LaneTableRow{"LN-088", "DEN", "BOS", "standard", 5, 8000, 720, false});
  out->push_back(LaneTableRow{"LN-089", "SEA", "STL", "intermodal", 6, 9500, 765, false});
  out->push_back(LaneTableRow{"LN-090", "PDX", "STL", "expedite", 1, 11000, 810, false});
  out->push_back(LaneTableRow{"LN-091", "OKC", "BOS", "flatbed", 2, 12500, 855, true});
  out->push_back(LaneTableRow{"LN-092", "NSH", "LAX", "reefer", 3, 14000, 900, false});
  out->push_back(LaneTableRow{"LN-093", "KCK", "ATL", "reefer", 4, 15500, 945, false});
  out->push_back(LaneTableRow{"LN-094", "ATL", "STL", "expedite", 5, 17000, 990, false});
  out->push_back(LaneTableRow{"LN-095", "KCK", "SEA", "flatbed", 6, 18500, 1035, false});
  out->push_back(LaneTableRow{"LN-096", "CHI", "LAX", "intermodal", 1, 20000, 1080, false});
  out->push_back(LaneTableRow{"LN-097", "DTW", "OKC", "standard", 2, 21500, 1125, false});
  out->push_back(LaneTableRow{"LN-098", "BOS", "STL", "flatbed", 3, 23000, 1170, true});
  out->push_back(LaneTableRow{"LN-099", "DTW", "OKC", "bonded", 4, 8000, 1215, false});
  out->push_back(LaneTableRow{"LN-100", "CHI", "BOS", "standard", 5, 9500, 1260, false});
  out->push_back(LaneTableRow{"LN-101", "CHI", "RNO", "flatbed", 6, 11000, 1305, false});
  out->push_back(LaneTableRow{"LN-102", "PHX", "DTW", "reefer", 1, 12500, 1350, false});
  out->push_back(LaneTableRow{"LN-103", "MSP", "LAX", "bonded", 2, 14000, 1395, false});
  out->push_back(LaneTableRow{"LN-104", "PDX", "CHI", "flatbed", 3, 15500, 1440, false});
  out->push_back(LaneTableRow{"LN-105", "TPA", "BOS", "flatbed", 4, 17000, 1485, true});
  out->push_back(LaneTableRow{"LN-106", "MSP", "STL", "intermodal", 5, 18500, 1530, false});
  out->push_back(LaneTableRow{"LN-107", "OKC", "LAX", "bonded", 6, 20000, 1575, false});
  out->push_back(LaneTableRow{"LN-108", "LAX", "YYZ", "bonded", 1, 21500, 1620, false});
  out->push_back(LaneTableRow{"LN-109", "JAX", "PHX", "expedite", 2, 23000, 1665, false});
  out->push_back(LaneTableRow{"LN-110", "SLC", "CHI", "standard", 3, 8000, 1710, false});
  out->push_back(LaneTableRow{"LN-111", "HOU", "SLC", "flatbed", 4, 9500, 1755, false});
  out->push_back(LaneTableRow{"LN-112", "STL", "PDX", "reefer", 5, 11000, 1800, true});
  out->push_back(LaneTableRow{"LN-113", "MSP", "OKC", "reefer", 6, 12500, 1845, false});
  out->push_back(LaneTableRow{"LN-114", "NSH", "YYZ", "intermodal", 1, 14000, 1890, false});
  out->push_back(LaneTableRow{"LN-115", "IND", "SLC", "flatbed", 2, 15500, 1935, false});
  out->push_back(LaneTableRow{"LN-116", "PHX", "JAX", "standard", 3, 17000, 1980, false});
  out->push_back(LaneTableRow{"LN-117", "TPA", "KCK", "intermodal", 4, 18500, 2025, false});
  out->push_back(LaneTableRow{"LN-118", "SLC", "HOU", "flatbed", 5, 20000, 2070, false});
  out->push_back(LaneTableRow{"LN-119", "BOS", "DFW", "flatbed", 6, 21500, 2115, true});
}

}  // namespace freight
