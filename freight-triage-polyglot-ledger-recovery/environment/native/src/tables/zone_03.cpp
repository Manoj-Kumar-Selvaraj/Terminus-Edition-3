#include "freight/tables.h"

namespace freight {

// zone table rows 180..239.
void zoneTableFill03(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-180", "Z80Y", 180, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-181", "Z81Z", 210, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-182", "Z82A", 240, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-183", "Z83B", 270, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-184", "Z84C", 300, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-185", "Z85D", 330, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-186", "Z86E", 345, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-187", "Z87F", 360, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-188", "Z88G", 390, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-189", "Z89H", 420, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-190", "Z90I", 480, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-191", "Z91J", 540, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-192", "Z92K", 570, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-193", "Z93L", 600, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-194", "Z94M", 660, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-195", "Z95N", 720, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-196", "Z96O", 780, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-197", "Z97P", 840, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-198", "Z98Q", -660, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-199", "Z99R", -600, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-200", "Z00S", -540, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-201", "Z01T", -480, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-202", "Z02U", -420, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-203", "Z03V", -360, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-204", "Z04W", -300, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-205", "Z05X", -240, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-206", "Z06Y", -210, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-207", "Z07Z", -180, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-208", "Z08A", -120, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-209", "Z09B", -60, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-210", "Z10C", 0, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-211", "Z11D", 60, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-212", "Z12E", 120, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-213", "Z13F", 180, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-214", "Z14G", 210, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-215", "Z15H", 240, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-216", "Z16I", 270, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-217", "Z17J", 300, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-218", "Z18K", 330, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-219", "Z19L", 345, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-220", "Z20M", 360, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-221", "Z21N", 390, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-222", "Z22O", 420, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-223", "Z23P", 480, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-224", "Z24Q", 540, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-225", "Z25R", 570, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-226", "Z26S", 600, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-227", "Z27T", 660, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-228", "Z28U", 720, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-229", "Z29V", 780, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-230", "Z30W", 840, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-231", "Z31X", -660, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-232", "Z32Y", -600, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-233", "Z33Z", -540, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-234", "Z34A", -480, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-235", "Z35B", -420, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-236", "Z36C", -360, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-237", "Z37D", -300, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-238", "Z38E", -240, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-239", "Z39F", -210, 0, "YVR"});
}

}  // namespace freight
