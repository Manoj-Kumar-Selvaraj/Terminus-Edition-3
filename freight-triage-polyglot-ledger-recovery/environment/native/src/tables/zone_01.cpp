#include "freight/tables.h"

namespace freight {

// zone table rows 60..119.
void zoneTableFill01(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-060", "Z60I", 570, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-061", "Z61J", 600, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-062", "Z62K", 660, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-063", "Z63L", 720, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-064", "Z64M", 780, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-065", "Z65N", 840, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-066", "Z66O", -660, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-067", "Z67P", -600, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-068", "Z68Q", -540, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-069", "Z69R", -480, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-070", "Z70S", -420, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-071", "Z71T", -360, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-072", "Z72U", -300, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-073", "Z73V", -240, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-074", "Z74W", -210, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-075", "Z75X", -180, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-076", "Z76Y", -120, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-077", "Z77Z", -60, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-078", "Z78A", 0, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-079", "Z79B", 60, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-080", "Z80C", 120, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-081", "Z81D", 180, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-082", "Z82E", 210, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-083", "Z83F", 240, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-084", "Z84G", 270, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-085", "Z85H", 300, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-086", "Z86I", 330, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-087", "Z87J", 345, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-088", "Z88K", 360, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-089", "Z89L", 390, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-090", "Z90M", 420, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-091", "Z91N", 480, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-092", "Z92O", 540, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-093", "Z93P", 570, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-094", "Z94Q", 600, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-095", "Z95R", 660, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-096", "Z96S", 720, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-097", "Z97T", 780, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-098", "Z98U", 840, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-099", "Z99V", -660, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-100", "Z00W", -600, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-101", "Z01X", -540, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-102", "Z02Y", -480, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-103", "Z03Z", -420, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-104", "Z04A", -360, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-105", "Z05B", -300, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-106", "Z06C", -240, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-107", "Z07D", -210, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-108", "Z08E", -180, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-109", "Z09F", -120, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-110", "Z10G", -60, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-111", "Z11H", 0, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-112", "Z12I", 60, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-113", "Z13J", 120, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-114", "Z14K", 180, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-115", "Z15L", 210, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-116", "Z16M", 240, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-117", "Z17N", 270, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-118", "Z18O", 300, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-119", "Z19P", 330, 0, "YVR"});
}

}  // namespace freight
