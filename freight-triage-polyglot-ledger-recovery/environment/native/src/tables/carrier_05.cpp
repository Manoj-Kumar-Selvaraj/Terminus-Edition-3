#include "freight/tables.h"

namespace freight {

// carrier table rows 300..359.
void carrierTableFill05(std::vector<CarrierTableRow>* out) {
  out->push_back(CarrierTableRow{"C300", "DWWD", "Carrier 300 Freight Systems", "ATL", 300000, true});
  out->push_back(CarrierTableRow{"C301", "JBSB", "Carrier 301 Freight Systems", "DEN", 312500, false});
  out->push_back(CarrierTableRow{"C302", "CLUD", "Carrier 302 Freight Systems", "DTW", 325000, false});
  out->push_back(CarrierTableRow{"C303", "OGZG", "Carrier 303 Freight Systems", "PHX", 337500, false});
  out->push_back(CarrierTableRow{"C304", "TESJ", "Carrier 304 Freight Systems", "CHI", 350000, false});
  out->push_back(CarrierTableRow{"C305", "UBQA", "Carrier 305 Freight Systems", "NSH", 362500, true});
  out->push_back(CarrierTableRow{"C306", "ZCWL", "Carrier 306 Freight Systems", "RNO", 375000, false});
  out->push_back(CarrierTableRow{"C307", "YTOP", "Carrier 307 Freight Systems", "TPA", 387500, false});
  out->push_back(CarrierTableRow{"C308", "ZDEE", "Carrier 308 Freight Systems", "STL", 400000, false});
  out->push_back(CarrierTableRow{"C309", "FUQD", "Carrier 309 Freight Systems", "BOS", 412500, false});
  out->push_back(CarrierTableRow{"C310", "OQNK", "Carrier 310 Freight Systems", "CHI", 425000, true});
  out->push_back(CarrierTableRow{"C311", "DIYK", "Carrier 311 Freight Systems", "ATL", 437500, false});
  out->push_back(CarrierTableRow{"C312", "TWBI", "Carrier 312 Freight Systems", "SLC", 450000, false});
  out->push_back(CarrierTableRow{"C313", "TGOS", "Carrier 313 Freight Systems", "RNO", 462500, false});
  out->push_back(CarrierTableRow{"C314", "ALYN", "Carrier 314 Freight Systems", "NSH", 475000, false});
  out->push_back(CarrierTableRow{"C315", "OXIK", "Carrier 315 Freight Systems", "DEN", 487500, true});
  out->push_back(CarrierTableRow{"C316", "ZFEG", "Carrier 316 Freight Systems", "HOU", 500000, false});
  out->push_back(CarrierTableRow{"C317", "EFDT", "Carrier 317 Freight Systems", "MSP", 512500, false});
  out->push_back(CarrierTableRow{"C318", "DYEX", "Carrier 318 Freight Systems", "RNO", 525000, false});
  out->push_back(CarrierTableRow{"C319", "JEPG", "Carrier 319 Freight Systems", "RNO", 537500, false});
  out->push_back(CarrierTableRow{"C320", "URMW", "Carrier 320 Freight Systems", "HOU", 550000, true});
  out->push_back(CarrierTableRow{"C321", "PRHX", "Carrier 321 Freight Systems", "OKC", 562500, false});
  out->push_back(CarrierTableRow{"C322", "LLGO", "Carrier 322 Freight Systems", "OKC", 575000, false});
  out->push_back(CarrierTableRow{"C323", "PTNZ", "Carrier 323 Freight Systems", "DEN", 587500, false});
  out->push_back(CarrierTableRow{"C324", "SQJK", "Carrier 324 Freight Systems", "SEA", 600000, false});
  out->push_back(CarrierTableRow{"C325", "BTKE", "Carrier 325 Freight Systems", "OKC", 612500, true});
  out->push_back(CarrierTableRow{"C326", "VRPN", "Carrier 326 Freight Systems", "OKC", 625000, false});
  out->push_back(CarrierTableRow{"C327", "FKJZ", "Carrier 327 Freight Systems", "SLC", 637500, false});
  out->push_back(CarrierTableRow{"C328", "YXPE", "Carrier 328 Freight Systems", "OKC", 650000, false});
  out->push_back(CarrierTableRow{"C329", "DKSH", "Carrier 329 Freight Systems", "SLC", 662500, false});
  out->push_back(CarrierTableRow{"C330", "SIVW", "Carrier 330 Freight Systems", "CHI", 675000, true});
  out->push_back(CarrierTableRow{"C331", "YQBF", "Carrier 331 Freight Systems", "PHX", 687500, false});
  out->push_back(CarrierTableRow{"C332", "HORM", "Carrier 332 Freight Systems", "JAX", 700000, false});
  out->push_back(CarrierTableRow{"C333", "YYJU", "Carrier 333 Freight Systems", "BOS", 250000, false});
  out->push_back(CarrierTableRow{"C334", "OYUN", "Carrier 334 Freight Systems", "MEM", 262500, false});
  out->push_back(CarrierTableRow{"C335", "HJHE", "Carrier 335 Freight Systems", "PDX", 275000, true});
  out->push_back(CarrierTableRow{"C336", "TXOP", "Carrier 336 Freight Systems", "TPA", 287500, false});
  out->push_back(CarrierTableRow{"C337", "OGVS", "Carrier 337 Freight Systems", "PHX", 300000, false});
  out->push_back(CarrierTableRow{"C338", "WZLE", "Carrier 338 Freight Systems", "STL", 312500, false});
  out->push_back(CarrierTableRow{"C339", "SDRS", "Carrier 339 Freight Systems", "YVR", 325000, false});
  out->push_back(CarrierTableRow{"C340", "RNMX", "Carrier 340 Freight Systems", "OKC", 337500, true});
  out->push_back(CarrierTableRow{"C341", "PRLB", "Carrier 341 Freight Systems", "YYZ", 350000, false});
  out->push_back(CarrierTableRow{"C342", "FNDX", "Carrier 342 Freight Systems", "PDX", 362500, false});
  out->push_back(CarrierTableRow{"C343", "MGDW", "Carrier 343 Freight Systems", "JAX", 375000, false});
  out->push_back(CarrierTableRow{"C344", "PPAY", "Carrier 344 Freight Systems", "STL", 387500, false});
  out->push_back(CarrierTableRow{"C345", "CQSR", "Carrier 345 Freight Systems", "RNO", 400000, true});
  out->push_back(CarrierTableRow{"C346", "ZMPE", "Carrier 346 Freight Systems", "PHX", 412500, false});
  out->push_back(CarrierTableRow{"C347", "FNTH", "Carrier 347 Freight Systems", "YVR", 425000, false});
  out->push_back(CarrierTableRow{"C348", "FIEB", "Carrier 348 Freight Systems", "RNO", 437500, false});
  out->push_back(CarrierTableRow{"C349", "HQNX", "Carrier 349 Freight Systems", "KCK", 450000, false});
  out->push_back(CarrierTableRow{"C350", "VVVH", "Carrier 350 Freight Systems", "PDX", 462500, true});
  out->push_back(CarrierTableRow{"C351", "TGSK", "Carrier 351 Freight Systems", "KCK", 475000, false});
  out->push_back(CarrierTableRow{"C352", "WHSC", "Carrier 352 Freight Systems", "STL", 487500, false});
  out->push_back(CarrierTableRow{"C353", "NIXD", "Carrier 353 Freight Systems", "LAX", 500000, false});
  out->push_back(CarrierTableRow{"C354", "NLGO", "Carrier 354 Freight Systems", "PDX", 512500, false});
  out->push_back(CarrierTableRow{"C355", "JCUQ", "Carrier 355 Freight Systems", "LAX", 525000, true});
  out->push_back(CarrierTableRow{"C356", "TGFO", "Carrier 356 Freight Systems", "KCK", 537500, false});
  out->push_back(CarrierTableRow{"C357", "MYDV", "Carrier 357 Freight Systems", "MEM", 550000, false});
  out->push_back(CarrierTableRow{"C358", "JTHL", "Carrier 358 Freight Systems", "YVR", 562500, false});
  out->push_back(CarrierTableRow{"C359", "DMUX", "Carrier 359 Freight Systems", "KCK", 575000, false});
}

}  // namespace freight
