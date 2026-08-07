#include "freight/tables.h"

namespace freight {

// carrier table rows 0..59.
void carrierTableFill00(std::vector<CarrierTableRow>* out) {
  out->push_back(CarrierTableRow{"C000", "RQLN", "Carrier 000 Freight Systems", "MEM", 250000, true});
  out->push_back(CarrierTableRow{"C001", "MGSN", "Carrier 001 Freight Systems", "SEA", 262500, false});
  out->push_back(CarrierTableRow{"C002", "ANLX", "Carrier 002 Freight Systems", "STL", 275000, false});
  out->push_back(CarrierTableRow{"C003", "UUUS", "Carrier 003 Freight Systems", "JAX", 287500, false});
  out->push_back(CarrierTableRow{"C004", "BRWD", "Carrier 004 Freight Systems", "DEN", 300000, false});
  out->push_back(CarrierTableRow{"C005", "FKDE", "Carrier 005 Freight Systems", "CHI", 312500, true});
  out->push_back(CarrierTableRow{"C006", "GTZE", "Carrier 006 Freight Systems", "YYZ", 325000, false});
  out->push_back(CarrierTableRow{"C007", "XVZE", "Carrier 007 Freight Systems", "DEN", 337500, false});
  out->push_back(CarrierTableRow{"C008", "OGSY", "Carrier 008 Freight Systems", "DFW", 350000, false});
  out->push_back(CarrierTableRow{"C009", "CACN", "Carrier 009 Freight Systems", "MEM", 362500, false});
  out->push_back(CarrierTableRow{"C010", "WZRH", "Carrier 010 Freight Systems", "DEN", 375000, true});
  out->push_back(CarrierTableRow{"C011", "NGZI", "Carrier 011 Freight Systems", "MEM", 387500, false});
  out->push_back(CarrierTableRow{"C012", "EJFU", "Carrier 012 Freight Systems", "IND", 400000, false});
  out->push_back(CarrierTableRow{"C013", "KFEN", "Carrier 013 Freight Systems", "DEN", 412500, false});
  out->push_back(CarrierTableRow{"C014", "XMVA", "Carrier 014 Freight Systems", "DFW", 425000, false});
  out->push_back(CarrierTableRow{"C015", "OLHS", "Carrier 015 Freight Systems", "YVR", 437500, true});
  out->push_back(CarrierTableRow{"C016", "IOCW", "Carrier 016 Freight Systems", "PHX", 450000, false});
  out->push_back(CarrierTableRow{"C017", "SWWU", "Carrier 017 Freight Systems", "SLC", 462500, false});
  out->push_back(CarrierTableRow{"C018", "XVAF", "Carrier 018 Freight Systems", "YVR", 475000, false});
  out->push_back(CarrierTableRow{"C019", "SNOY", "Carrier 019 Freight Systems", "HOU", 487500, false});
  out->push_back(CarrierTableRow{"C020", "KIDE", "Carrier 020 Freight Systems", "BOS", 500000, true});
  out->push_back(CarrierTableRow{"C021", "TYHV", "Carrier 021 Freight Systems", "DFW", 512500, false});
  out->push_back(CarrierTableRow{"C022", "PKVA", "Carrier 022 Freight Systems", "PHX", 525000, false});
  out->push_back(CarrierTableRow{"C023", "OZAV", "Carrier 023 Freight Systems", "HOU", 537500, false});
  out->push_back(CarrierTableRow{"C024", "GAEK", "Carrier 024 Freight Systems", "PHX", 550000, false});
  out->push_back(CarrierTableRow{"C025", "GAOP", "Carrier 025 Freight Systems", "JAX", 562500, true});
  out->push_back(CarrierTableRow{"C026", "EZMV", "Carrier 026 Freight Systems", "DTW", 575000, false});
  out->push_back(CarrierTableRow{"C027", "WVQZ", "Carrier 027 Freight Systems", "STL", 587500, false});
  out->push_back(CarrierTableRow{"C028", "LOYE", "Carrier 028 Freight Systems", "PHX", 600000, false});
  out->push_back(CarrierTableRow{"C029", "ARAP", "Carrier 029 Freight Systems", "YVR", 612500, false});
  out->push_back(CarrierTableRow{"C030", "AWAL", "Carrier 030 Freight Systems", "DFW", 625000, true});
  out->push_back(CarrierTableRow{"C031", "CYAG", "Carrier 031 Freight Systems", "KCK", 637500, false});
  out->push_back(CarrierTableRow{"C032", "BMPA", "Carrier 032 Freight Systems", "PHX", 650000, false});
  out->push_back(CarrierTableRow{"C033", "MJAX", "Carrier 033 Freight Systems", "DTW", 662500, false});
  out->push_back(CarrierTableRow{"C034", "NEXK", "Carrier 034 Freight Systems", "RNO", 675000, false});
  out->push_back(CarrierTableRow{"C035", "JSPE", "Carrier 035 Freight Systems", "SEA", 687500, true});
  out->push_back(CarrierTableRow{"C036", "THRO", "Carrier 036 Freight Systems", "MSP", 700000, false});
  out->push_back(CarrierTableRow{"C037", "YNRE", "Carrier 037 Freight Systems", "IND", 250000, false});
  out->push_back(CarrierTableRow{"C038", "RUAX", "Carrier 038 Freight Systems", "ATL", 262500, false});
  out->push_back(CarrierTableRow{"C039", "WMCO", "Carrier 039 Freight Systems", "SEA", 275000, false});
  out->push_back(CarrierTableRow{"C040", "WJUA", "Carrier 040 Freight Systems", "YYZ", 287500, true});
  out->push_back(CarrierTableRow{"C041", "QPIN", "Carrier 041 Freight Systems", "YVR", 300000, false});
  out->push_back(CarrierTableRow{"C042", "KZUD", "Carrier 042 Freight Systems", "OKC", 312500, false});
  out->push_back(CarrierTableRow{"C043", "VMKR", "Carrier 043 Freight Systems", "SEA", 325000, false});
  out->push_back(CarrierTableRow{"C044", "TZTB", "Carrier 044 Freight Systems", "PDX", 337500, false});
  out->push_back(CarrierTableRow{"C045", "JOCG", "Carrier 045 Freight Systems", "PHX", 350000, true});
  out->push_back(CarrierTableRow{"C046", "WGBR", "Carrier 046 Freight Systems", "BOS", 362500, false});
  out->push_back(CarrierTableRow{"C047", "LFKU", "Carrier 047 Freight Systems", "DEN", 375000, false});
  out->push_back(CarrierTableRow{"C048", "DGIH", "Carrier 048 Freight Systems", "LAX", 387500, false});
  out->push_back(CarrierTableRow{"C049", "TWPV", "Carrier 049 Freight Systems", "LAX", 400000, false});
  out->push_back(CarrierTableRow{"C050", "CRCF", "Carrier 050 Freight Systems", "STL", 412500, true});
  out->push_back(CarrierTableRow{"C051", "RATY", "Carrier 051 Freight Systems", "LAX", 425000, false});
  out->push_back(CarrierTableRow{"C052", "QCHO", "Carrier 052 Freight Systems", "ATL", 437500, false});
  out->push_back(CarrierTableRow{"C053", "TBQE", "Carrier 053 Freight Systems", "NSH", 450000, false});
  out->push_back(CarrierTableRow{"C054", "VMOV", "Carrier 054 Freight Systems", "SEA", 462500, false});
  out->push_back(CarrierTableRow{"C055", "IWZW", "Carrier 055 Freight Systems", "JAX", 475000, true});
  out->push_back(CarrierTableRow{"C056", "MPCL", "Carrier 056 Freight Systems", "MSP", 487500, false});
  out->push_back(CarrierTableRow{"C057", "KNBR", "Carrier 057 Freight Systems", "DTW", 500000, false});
  out->push_back(CarrierTableRow{"C058", "ULGL", "Carrier 058 Freight Systems", "STL", 512500, false});
  out->push_back(CarrierTableRow{"C059", "BWCL", "Carrier 059 Freight Systems", "SEA", 525000, false});
}

}  // namespace freight
