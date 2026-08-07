#include "freight/tables.h"

namespace freight {

// zone table rows 120..179.
void zoneTableFill02(std::vector<ZoneTableRow>* out) {
  out->push_back(ZoneTableRow{"FZ-120", "Z20Q", 345, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-121", "Z21R", 360, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-122", "Z22S", 390, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-123", "Z23T", 420, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-124", "Z24U", 480, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-125", "Z25V", 540, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-126", "Z26W", 570, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-127", "Z27X", 600, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-128", "Z28Y", 660, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-129", "Z29Z", 720, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-130", "Z30A", 780, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-131", "Z31B", 840, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-132", "Z32C", -660, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-133", "Z33D", -600, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-134", "Z34E", -540, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-135", "Z35F", -480, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-136", "Z36G", -420, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-137", "Z37H", -360, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-138", "Z38I", -300, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-139", "Z39J", -240, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-140", "Z40K", -210, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-141", "Z41L", -180, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-142", "Z42M", -120, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-143", "Z43N", -60, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-144", "Z44O", 0, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-145", "Z45P", 60, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-146", "Z46Q", 120, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-147", "Z47R", 180, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-148", "Z48S", 210, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-149", "Z49T", 240, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-150", "Z50U", 270, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-151", "Z51V", 300, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-152", "Z52W", 330, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-153", "Z53X", 345, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-154", "Z54Y", 360, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-155", "Z55Z", 390, 0, "MEM"});
  out->push_back(ZoneTableRow{"FZ-156", "Z56A", 420, 60, "MSP"});
  out->push_back(ZoneTableRow{"FZ-157", "Z57B", 480, 0, "NSH"});
  out->push_back(ZoneTableRow{"FZ-158", "Z58C", 540, 0, "OKC"});
  out->push_back(ZoneTableRow{"FZ-159", "Z59D", 570, 0, "PDX"});
  out->push_back(ZoneTableRow{"FZ-160", "Z60E", 600, 60, "PHX"});
  out->push_back(ZoneTableRow{"FZ-161", "Z61F", 660, 0, "RNO"});
  out->push_back(ZoneTableRow{"FZ-162", "Z62G", 720, 0, "SLC"});
  out->push_back(ZoneTableRow{"FZ-163", "Z63H", 780, 0, "SEA"});
  out->push_back(ZoneTableRow{"FZ-164", "Z64I", 840, 60, "STL"});
  out->push_back(ZoneTableRow{"FZ-165", "Z65J", -660, 0, "TPA"});
  out->push_back(ZoneTableRow{"FZ-166", "Z66K", -600, 0, "YYZ"});
  out->push_back(ZoneTableRow{"FZ-167", "Z67L", -540, 0, "YVR"});
  out->push_back(ZoneTableRow{"FZ-168", "Z68M", -480, 60, "ATL"});
  out->push_back(ZoneTableRow{"FZ-169", "Z69N", -420, 0, "BOS"});
  out->push_back(ZoneTableRow{"FZ-170", "Z70O", -360, 0, "CHI"});
  out->push_back(ZoneTableRow{"FZ-171", "Z71P", -300, 0, "DFW"});
  out->push_back(ZoneTableRow{"FZ-172", "Z72Q", -240, 60, "DEN"});
  out->push_back(ZoneTableRow{"FZ-173", "Z73R", -210, 0, "DTW"});
  out->push_back(ZoneTableRow{"FZ-174", "Z74S", -180, 0, "HOU"});
  out->push_back(ZoneTableRow{"FZ-175", "Z75T", -120, 0, "IND"});
  out->push_back(ZoneTableRow{"FZ-176", "Z76U", -60, 60, "JAX"});
  out->push_back(ZoneTableRow{"FZ-177", "Z77V", 0, 0, "KCK"});
  out->push_back(ZoneTableRow{"FZ-178", "Z78W", 60, 0, "LAX"});
  out->push_back(ZoneTableRow{"FZ-179", "Z79X", 120, 0, "MEM"});
}

}  // namespace freight
