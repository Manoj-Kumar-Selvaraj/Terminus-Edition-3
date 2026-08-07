#include "freight/tables.h"

namespace freight {

// carrier table rows 180..239.
void carrierTableFill03(std::vector<CarrierTableRow>* out) {
  out->push_back(CarrierTableRow{"C180", "ENUX", "Carrier 180 Freight Systems", "PDX", 650000, true});
  out->push_back(CarrierTableRow{"C181", "SYDI", "Carrier 181 Freight Systems", "SEA", 662500, false});
  out->push_back(CarrierTableRow{"C182", "ZLYZ", "Carrier 182 Freight Systems", "TPA", 675000, false});
  out->push_back(CarrierTableRow{"C183", "MYAJ", "Carrier 183 Freight Systems", "MEM", 687500, false});
  out->push_back(CarrierTableRow{"C184", "LMNM", "Carrier 184 Freight Systems", "LAX", 700000, false});
  out->push_back(CarrierTableRow{"C185", "PGIY", "Carrier 185 Freight Systems", "MEM", 250000, true});
  out->push_back(CarrierTableRow{"C186", "SLUH", "Carrier 186 Freight Systems", "PDX", 262500, false});
  out->push_back(CarrierTableRow{"C187", "RSDO", "Carrier 187 Freight Systems", "BOS", 275000, false});
  out->push_back(CarrierTableRow{"C188", "CWPQ", "Carrier 188 Freight Systems", "SEA", 287500, false});
  out->push_back(CarrierTableRow{"C189", "QYIY", "Carrier 189 Freight Systems", "PHX", 300000, false});
  out->push_back(CarrierTableRow{"C190", "MNWZ", "Carrier 190 Freight Systems", "NSH", 312500, true});
  out->push_back(CarrierTableRow{"C191", "TQYO", "Carrier 191 Freight Systems", "ATL", 325000, false});
  out->push_back(CarrierTableRow{"C192", "IFWQ", "Carrier 192 Freight Systems", "YVR", 337500, false});
  out->push_back(CarrierTableRow{"C193", "URXF", "Carrier 193 Freight Systems", "HOU", 350000, false});
  out->push_back(CarrierTableRow{"C194", "TKYO", "Carrier 194 Freight Systems", "RNO", 362500, false});
  out->push_back(CarrierTableRow{"C195", "SQCD", "Carrier 195 Freight Systems", "ATL", 375000, true});
  out->push_back(CarrierTableRow{"C196", "WHBC", "Carrier 196 Freight Systems", "STL", 387500, false});
  out->push_back(CarrierTableRow{"C197", "PXZO", "Carrier 197 Freight Systems", "STL", 400000, false});
  out->push_back(CarrierTableRow{"C198", "GWJO", "Carrier 198 Freight Systems", "DFW", 412500, false});
  out->push_back(CarrierTableRow{"C199", "FWJK", "Carrier 199 Freight Systems", "SEA", 425000, false});
  out->push_back(CarrierTableRow{"C200", "AARN", "Carrier 200 Freight Systems", "MEM", 437500, true});
  out->push_back(CarrierTableRow{"C201", "WALH", "Carrier 201 Freight Systems", "SLC", 450000, false});
  out->push_back(CarrierTableRow{"C202", "ZSXZ", "Carrier 202 Freight Systems", "LAX", 462500, false});
  out->push_back(CarrierTableRow{"C203", "VSOS", "Carrier 203 Freight Systems", "CHI", 475000, false});
  out->push_back(CarrierTableRow{"C204", "KOUT", "Carrier 204 Freight Systems", "ATL", 487500, false});
  out->push_back(CarrierTableRow{"C205", "GOHA", "Carrier 205 Freight Systems", "SEA", 500000, true});
  out->push_back(CarrierTableRow{"C206", "VMFM", "Carrier 206 Freight Systems", "ATL", 512500, false});
  out->push_back(CarrierTableRow{"C207", "AEQC", "Carrier 207 Freight Systems", "DFW", 525000, false});
  out->push_back(CarrierTableRow{"C208", "NNZB", "Carrier 208 Freight Systems", "TPA", 537500, false});
  out->push_back(CarrierTableRow{"C209", "VMLZ", "Carrier 209 Freight Systems", "PHX", 550000, false});
  out->push_back(CarrierTableRow{"C210", "DAOQ", "Carrier 210 Freight Systems", "PHX", 562500, true});
  out->push_back(CarrierTableRow{"C211", "MBOE", "Carrier 211 Freight Systems", "DEN", 575000, false});
  out->push_back(CarrierTableRow{"C212", "GPNM", "Carrier 212 Freight Systems", "OKC", 587500, false});
  out->push_back(CarrierTableRow{"C213", "FQPZ", "Carrier 213 Freight Systems", "RNO", 600000, false});
  out->push_back(CarrierTableRow{"C214", "LMCS", "Carrier 214 Freight Systems", "SLC", 612500, false});
  out->push_back(CarrierTableRow{"C215", "NOHC", "Carrier 215 Freight Systems", "ATL", 625000, true});
  out->push_back(CarrierTableRow{"C216", "BCVW", "Carrier 216 Freight Systems", "RNO", 637500, false});
  out->push_back(CarrierTableRow{"C217", "KHQS", "Carrier 217 Freight Systems", "YYZ", 650000, false});
  out->push_back(CarrierTableRow{"C218", "KQXG", "Carrier 218 Freight Systems", "LAX", 662500, false});
  out->push_back(CarrierTableRow{"C219", "IVGG", "Carrier 219 Freight Systems", "NSH", 675000, false});
  out->push_back(CarrierTableRow{"C220", "SYPE", "Carrier 220 Freight Systems", "MEM", 687500, true});
  out->push_back(CarrierTableRow{"C221", "DMED", "Carrier 221 Freight Systems", "KCK", 700000, false});
  out->push_back(CarrierTableRow{"C222", "TVQH", "Carrier 222 Freight Systems", "HOU", 250000, false});
  out->push_back(CarrierTableRow{"C223", "ZUCL", "Carrier 223 Freight Systems", "RNO", 262500, false});
  out->push_back(CarrierTableRow{"C224", "NQCA", "Carrier 224 Freight Systems", "CHI", 275000, false});
  out->push_back(CarrierTableRow{"C225", "SEKM", "Carrier 225 Freight Systems", "CHI", 287500, true});
  out->push_back(CarrierTableRow{"C226", "NCCY", "Carrier 226 Freight Systems", "MEM", 300000, false});
  out->push_back(CarrierTableRow{"C227", "DAMW", "Carrier 227 Freight Systems", "SEA", 312500, false});
  out->push_back(CarrierTableRow{"C228", "BQUB", "Carrier 228 Freight Systems", "RNO", 325000, false});
  out->push_back(CarrierTableRow{"C229", "JSDW", "Carrier 229 Freight Systems", "JAX", 337500, false});
  out->push_back(CarrierTableRow{"C230", "WMZG", "Carrier 230 Freight Systems", "ATL", 350000, true});
  out->push_back(CarrierTableRow{"C231", "MGBZ", "Carrier 231 Freight Systems", "MEM", 362500, false});
  out->push_back(CarrierTableRow{"C232", "VZVD", "Carrier 232 Freight Systems", "PDX", 375000, false});
  out->push_back(CarrierTableRow{"C233", "VZMT", "Carrier 233 Freight Systems", "YVR", 387500, false});
  out->push_back(CarrierTableRow{"C234", "WDMT", "Carrier 234 Freight Systems", "PDX", 400000, false});
  out->push_back(CarrierTableRow{"C235", "NTZG", "Carrier 235 Freight Systems", "DEN", 412500, true});
  out->push_back(CarrierTableRow{"C236", "XINK", "Carrier 236 Freight Systems", "ATL", 425000, false});
  out->push_back(CarrierTableRow{"C237", "MYRH", "Carrier 237 Freight Systems", "SEA", 437500, false});
  out->push_back(CarrierTableRow{"C238", "QPYC", "Carrier 238 Freight Systems", "MSP", 450000, false});
  out->push_back(CarrierTableRow{"C239", "WGBE", "Carrier 239 Freight Systems", "KCK", 462500, false});
}

}  // namespace freight
