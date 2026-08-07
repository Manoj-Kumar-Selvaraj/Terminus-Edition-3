#include "freight/tables.h"

namespace freight {

// carrier table rows 60..119.
void carrierTableFill01(std::vector<CarrierTableRow>* out) {
  out->push_back(CarrierTableRow{"C060", "RJUX", "Carrier 060 Freight Systems", "NSH", 537500, true});
  out->push_back(CarrierTableRow{"C061", "LTSA", "Carrier 061 Freight Systems", "YVR", 550000, false});
  out->push_back(CarrierTableRow{"C062", "NEAE", "Carrier 062 Freight Systems", "RNO", 562500, false});
  out->push_back(CarrierTableRow{"C063", "TLUB", "Carrier 063 Freight Systems", "MSP", 575000, false});
  out->push_back(CarrierTableRow{"C064", "UFJB", "Carrier 064 Freight Systems", "OKC", 587500, false});
  out->push_back(CarrierTableRow{"C065", "AGLA", "Carrier 065 Freight Systems", "CHI", 600000, true});
  out->push_back(CarrierTableRow{"C066", "QFUK", "Carrier 066 Freight Systems", "DTW", 612500, false});
  out->push_back(CarrierTableRow{"C067", "JJDZ", "Carrier 067 Freight Systems", "STL", 625000, false});
  out->push_back(CarrierTableRow{"C068", "ICLA", "Carrier 068 Freight Systems", "LAX", 637500, false});
  out->push_back(CarrierTableRow{"C069", "SDQW", "Carrier 069 Freight Systems", "PDX", 650000, false});
  out->push_back(CarrierTableRow{"C070", "YRCQ", "Carrier 070 Freight Systems", "STL", 662500, true});
  out->push_back(CarrierTableRow{"C071", "ZDZJ", "Carrier 071 Freight Systems", "DEN", 675000, false});
  out->push_back(CarrierTableRow{"C072", "WEZG", "Carrier 072 Freight Systems", "MEM", 687500, false});
  out->push_back(CarrierTableRow{"C073", "AKKM", "Carrier 073 Freight Systems", "LAX", 700000, false});
  out->push_back(CarrierTableRow{"C074", "JDQD", "Carrier 074 Freight Systems", "OKC", 250000, false});
  out->push_back(CarrierTableRow{"C075", "OWBQ", "Carrier 075 Freight Systems", "RNO", 262500, true});
  out->push_back(CarrierTableRow{"C076", "RPIT", "Carrier 076 Freight Systems", "YVR", 275000, false});
  out->push_back(CarrierTableRow{"C077", "GOZB", "Carrier 077 Freight Systems", "ATL", 287500, false});
  out->push_back(CarrierTableRow{"C078", "HGHP", "Carrier 078 Freight Systems", "CHI", 300000, false});
  out->push_back(CarrierTableRow{"C079", "HFYJ", "Carrier 079 Freight Systems", "YVR", 312500, false});
  out->push_back(CarrierTableRow{"C080", "UEOF", "Carrier 080 Freight Systems", "LAX", 325000, true});
  out->push_back(CarrierTableRow{"C081", "TXZU", "Carrier 081 Freight Systems", "TPA", 337500, false});
  out->push_back(CarrierTableRow{"C082", "YMKS", "Carrier 082 Freight Systems", "JAX", 350000, false});
  out->push_back(CarrierTableRow{"C083", "HJEJ", "Carrier 083 Freight Systems", "YVR", 362500, false});
  out->push_back(CarrierTableRow{"C084", "MGEX", "Carrier 084 Freight Systems", "MEM", 375000, false});
  out->push_back(CarrierTableRow{"C085", "BENT", "Carrier 085 Freight Systems", "DFW", 387500, true});
  out->push_back(CarrierTableRow{"C086", "KJUU", "Carrier 086 Freight Systems", "DTW", 400000, false});
  out->push_back(CarrierTableRow{"C087", "AVPE", "Carrier 087 Freight Systems", "STL", 412500, false});
  out->push_back(CarrierTableRow{"C088", "QUIR", "Carrier 088 Freight Systems", "SEA", 425000, false});
  out->push_back(CarrierTableRow{"C089", "CUYM", "Carrier 089 Freight Systems", "RNO", 437500, false});
  out->push_back(CarrierTableRow{"C090", "NJPW", "Carrier 090 Freight Systems", "NSH", 450000, true});
  out->push_back(CarrierTableRow{"C091", "EGHW", "Carrier 091 Freight Systems", "CHI", 462500, false});
  out->push_back(CarrierTableRow{"C092", "RZSM", "Carrier 092 Freight Systems", "YYZ", 475000, false});
  out->push_back(CarrierTableRow{"C093", "JQJT", "Carrier 093 Freight Systems", "SLC", 487500, false});
  out->push_back(CarrierTableRow{"C094", "RARL", "Carrier 094 Freight Systems", "SLC", 500000, false});
  out->push_back(CarrierTableRow{"C095", "KBOL", "Carrier 095 Freight Systems", "STL", 512500, true});
  out->push_back(CarrierTableRow{"C096", "WJSA", "Carrier 096 Freight Systems", "OKC", 525000, false});
  out->push_back(CarrierTableRow{"C097", "VUHY", "Carrier 097 Freight Systems", "PHX", 537500, false});
  out->push_back(CarrierTableRow{"C098", "BLCY", "Carrier 098 Freight Systems", "DTW", 550000, false});
  out->push_back(CarrierTableRow{"C099", "XZIT", "Carrier 099 Freight Systems", "MSP", 562500, false});
  out->push_back(CarrierTableRow{"C100", "LTTB", "Carrier 100 Freight Systems", "IND", 575000, true});
  out->push_back(CarrierTableRow{"C101", "OSFY", "Carrier 101 Freight Systems", "RNO", 587500, false});
  out->push_back(CarrierTableRow{"C102", "XPIE", "Carrier 102 Freight Systems", "DTW", 600000, false});
  out->push_back(CarrierTableRow{"C103", "RPRC", "Carrier 103 Freight Systems", "MSP", 612500, false});
  out->push_back(CarrierTableRow{"C104", "TNOF", "Carrier 104 Freight Systems", "YYZ", 625000, false});
  out->push_back(CarrierTableRow{"C105", "KDNC", "Carrier 105 Freight Systems", "YYZ", 637500, true});
  out->push_back(CarrierTableRow{"C106", "GNKZ", "Carrier 106 Freight Systems", "STL", 650000, false});
  out->push_back(CarrierTableRow{"C107", "XOWG", "Carrier 107 Freight Systems", "LAX", 662500, false});
  out->push_back(CarrierTableRow{"C108", "OGST", "Carrier 108 Freight Systems", "PHX", 675000, false});
  out->push_back(CarrierTableRow{"C109", "CBKK", "Carrier 109 Freight Systems", "YYZ", 687500, false});
  out->push_back(CarrierTableRow{"C110", "MSJM", "Carrier 110 Freight Systems", "RNO", 700000, true});
  out->push_back(CarrierTableRow{"C111", "BAAO", "Carrier 111 Freight Systems", "DFW", 250000, false});
  out->push_back(CarrierTableRow{"C112", "LXHK", "Carrier 112 Freight Systems", "IND", 262500, false});
  out->push_back(CarrierTableRow{"C113", "PGIU", "Carrier 113 Freight Systems", "JAX", 275000, false});
  out->push_back(CarrierTableRow{"C114", "EVMT", "Carrier 114 Freight Systems", "DTW", 287500, false});
  out->push_back(CarrierTableRow{"C115", "ORYD", "Carrier 115 Freight Systems", "YYZ", 300000, true});
  out->push_back(CarrierTableRow{"C116", "NGWN", "Carrier 116 Freight Systems", "ATL", 312500, false});
  out->push_back(CarrierTableRow{"C117", "VDER", "Carrier 117 Freight Systems", "DEN", 325000, false});
  out->push_back(CarrierTableRow{"C118", "WRWW", "Carrier 118 Freight Systems", "IND", 337500, false});
  out->push_back(CarrierTableRow{"C119", "RANG", "Carrier 119 Freight Systems", "LAX", 350000, false});
}

}  // namespace freight
