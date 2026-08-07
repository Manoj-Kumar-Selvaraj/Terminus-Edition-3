#include "freight/tables.h"

namespace freight {

// zone table rows 300..319.
void zoneTableFill05(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-300", "Z00O", -480, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-301", "Z01P", -420, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-302", "Z02Q", -360, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-303", "Z03R", -300, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-304", "Z04S", -240, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-305", "Z05T", -210, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-306", "Z06U", -180, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-307", "Z07V", -120, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-308", "Z08W", -60, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-309", "Z09X", 0, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-310", "Z10Y", 60, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-311", "Z11Z", 120, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-312", "Z12A", 180, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-313", "Z13B", 210, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-314", "Z14C", 240, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-315", "Z15D", 270, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-316", "Z16E", 300, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-317", "Z17F", 330, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-318", "Z18G", 345, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-319", "Z19H", 360, 0, "IND"});
}

}  // namespace freight
