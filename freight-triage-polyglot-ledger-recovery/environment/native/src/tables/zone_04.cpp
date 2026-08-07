#include "freight/tables.h"

namespace freight {

// zone table rows 240..299.
void zoneTableFill04(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-240", "Z40G", -180, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-241", "Z41H", -120, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-242", "Z42I", -60, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-243", "Z43J", 0, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-244", "Z44K", 60, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-245", "Z45L", 120, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-246", "Z46M", 180, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-247", "Z47N", 210, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-248", "Z48O", 240, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-249", "Z49P", 270, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-250", "Z50Q", 300, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-251", "Z51R", 330, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-252", "Z52S", 345, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-253", "Z53T", 360, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-254", "Z54U", 390, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-255", "Z55V", 420, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-256", "Z56W", 480, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-257", "Z57X", 540, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-258", "Z58Y", 570, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-259", "Z59Z", 600, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-260", "Z60A", 660, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-261", "Z61B", 720, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-262", "Z62C", 780, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-263", "Z63D", 840, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-264", "Z64E", -660, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-265", "Z65F", -600, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-266", "Z66G", -540, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-267", "Z67H", -480, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-268", "Z68I", -420, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-269", "Z69J", -360, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-270", "Z70K", -300, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-271", "Z71L", -240, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-272", "Z72M", -210, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-273", "Z73N", -180, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-274", "Z74O", -120, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-275", "Z75P", -60, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-276", "Z76Q", 0, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-277", "Z77R", 60, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-278", "Z78S", 120, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-279", "Z79T", 180, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-280", "Z80U", 210, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-281", "Z81V", 240, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-282", "Z82W", 270, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-283", "Z83X", 300, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-284", "Z84Y", 330, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-285", "Z85Z", 345, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-286", "Z86A", 360, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-287", "Z87B", 390, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-288", "Z88C", 420, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-289", "Z89D", 480, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-290", "Z90E", 540, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-291", "Z91F", 570, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-292", "Z92G", 600, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-293", "Z93H", 660, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-294", "Z94I", 720, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-295", "Z95J", 780, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-296", "Z96K", 840, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-297", "Z97L", -660, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-298", "Z98M", -600, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-299", "Z99N", -540, 0, "MEM"});
}

}  // namespace freight
