#include "freight/tables.h"

namespace freight {

// zone table rows 0..59.
void zoneTableFill00(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-000", "Z00A", -660, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-001", "Z01B", -600, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-002", "Z02C", -540, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-003", "Z03D", -480, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-004", "Z04E", -420, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-005", "Z05F", -360, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-006", "Z06G", -300, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-007", "Z07H", -240, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-008", "Z08I", -210, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-009", "Z09J", -180, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-010", "Z10K", -120, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-011", "Z11L", -60, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-012", "Z12M", 0, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-013", "Z13N", 60, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-014", "Z14O", 120, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-015", "Z15P", 180, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-016", "Z16Q", 210, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-017", "Z17R", 240, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-018", "Z18S", 270, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-019", "Z19T", 300, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-020", "Z20U", 330, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-021", "Z21V", 345, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-022", "Z22W", 360, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-023", "Z23X", 390, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-024", "Z24Y", 420, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-025", "Z25Z", 480, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-026", "Z26A", 540, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-027", "Z27B", 570, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-028", "Z28C", 600, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-029", "Z29D", 660, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-030", "Z30E", 720, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-031", "Z31F", 780, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-032", "Z32G", 840, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-033", "Z33H", -660, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-034", "Z34I", -600, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-035", "Z35J", -540, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-036", "Z36K", -480, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-037", "Z37L", -420, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-038", "Z38M", -360, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-039", "Z39N", -300, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-040", "Z40O", -240, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-041", "Z41P", -210, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-042", "Z42Q", -180, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-043", "Z43R", -120, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-044", "Z44S", -60, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-045", "Z45T", 0, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-046", "Z46U", 60, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-047", "Z47V", 120, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-048", "Z48W", 180, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-049", "Z49X", 210, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-050", "Z50Y", 240, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-051", "Z51Z", 270, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-052", "Z52A", 300, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-053", "Z53B", 330, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-054", "Z54C", 345, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-055", "Z55D", 360, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-056", "Z56E", 390, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-057", "Z57F", 420, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-058", "Z58G", 480, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-059", "Z59H", 540, 0, "MEM"});
}

}  // namespace freight
