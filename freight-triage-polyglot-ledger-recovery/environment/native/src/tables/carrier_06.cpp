#include "freight/tables.h"

namespace freight {

// carrier table rows 360..419.
void carrierTableFill06(std::vector<CarrierTableRow>* out) {
  out->push_back(CarrierTableRow{"C360", "KOTY", "Carrier 360 Freight Systems", "DFW", 587500, true});
  out->push_back(CarrierTableRow{"C361", "NOOS", "Carrier 361 Freight Systems", "ATL", 600000, false});
  out->push_back(CarrierTableRow{"C362", "NRIG", "Carrier 362 Freight Systems", "DTW", 612500, false});
  out->push_back(CarrierTableRow{"C363", "CNVV", "Carrier 363 Freight Systems", "YVR", 625000, false});
  out->push_back(CarrierTableRow{"C364", "GJSW", "Carrier 364 Freight Systems", "STL", 637500, false});
  out->push_back(CarrierTableRow{"C365", "IWMC", "Carrier 365 Freight Systems", "JAX", 650000, true});
  out->push_back(CarrierTableRow{"C366", "CSYK", "Carrier 366 Freight Systems", "MEM", 662500, false});
  out->push_back(CarrierTableRow{"C367", "HLDO", "Carrier 367 Freight Systems", "YYZ", 675000, false});
  out->push_back(CarrierTableRow{"C368", "RPLV", "Carrier 368 Freight Systems", "DEN", 687500, false});
  out->push_back(CarrierTableRow{"C369", "IMJE", "Carrier 369 Freight Systems", "KCK", 700000, false});
  out->push_back(CarrierTableRow{"C370", "TSHQ", "Carrier 370 Freight Systems", "RNO", 250000, true});
  out->push_back(CarrierTableRow{"C371", "NTLA", "Carrier 371 Freight Systems", "MSP", 262500, false});
  out->push_back(CarrierTableRow{"C372", "MLKE", "Carrier 372 Freight Systems", "PDX", 275000, false});
  out->push_back(CarrierTableRow{"C373", "STFS", "Carrier 373 Freight Systems", "DTW", 287500, false});
  out->push_back(CarrierTableRow{"C374", "XNQH", "Carrier 374 Freight Systems", "HOU", 300000, false});
  out->push_back(CarrierTableRow{"C375", "PVZZ", "Carrier 375 Freight Systems", "HOU", 312500, true});
  out->push_back(CarrierTableRow{"C376", "WQWJ", "Carrier 376 Freight Systems", "PHX", 325000, false});
  out->push_back(CarrierTableRow{"C377", "YJKG", "Carrier 377 Freight Systems", "YYZ", 337500, false});
  out->push_back(CarrierTableRow{"C378", "WBRL", "Carrier 378 Freight Systems", "YYZ", 350000, false});
  out->push_back(CarrierTableRow{"C379", "CNGY", "Carrier 379 Freight Systems", "IND", 362500, false});
  out->push_back(CarrierTableRow{"C380", "LTET", "Carrier 380 Freight Systems", "IND", 375000, true});
  out->push_back(CarrierTableRow{"C381", "ZGBM", "Carrier 381 Freight Systems", "RNO", 387500, false});
  out->push_back(CarrierTableRow{"C382", "TDEI", "Carrier 382 Freight Systems", "PDX", 400000, false});
  out->push_back(CarrierTableRow{"C383", "HWLW", "Carrier 383 Freight Systems", "SEA", 412500, false});
  out->push_back(CarrierTableRow{"C384", "GJMT", "Carrier 384 Freight Systems", "DEN", 425000, false});
  out->push_back(CarrierTableRow{"C385", "JCJX", "Carrier 385 Freight Systems", "SLC", 437500, true});
  out->push_back(CarrierTableRow{"C386", "ZPLU", "Carrier 386 Freight Systems", "NSH", 450000, false});
  out->push_back(CarrierTableRow{"C387", "LCNK", "Carrier 387 Freight Systems", "SEA", 462500, false});
  out->push_back(CarrierTableRow{"C388", "FDXV", "Carrier 388 Freight Systems", "NSH", 475000, false});
  out->push_back(CarrierTableRow{"C389", "ZWLE", "Carrier 389 Freight Systems", "CHI", 487500, false});
  out->push_back(CarrierTableRow{"C390", "UFZI", "Carrier 390 Freight Systems", "YYZ", 500000, true});
  out->push_back(CarrierTableRow{"C391", "PDTD", "Carrier 391 Freight Systems", "YYZ", 512500, false});
  out->push_back(CarrierTableRow{"C392", "CQPT", "Carrier 392 Freight Systems", "RNO", 525000, false});
  out->push_back(CarrierTableRow{"C393", "EHJZ", "Carrier 393 Freight Systems", "DTW", 537500, false});
  out->push_back(CarrierTableRow{"C394", "MZMA", "Carrier 394 Freight Systems", "YYZ", 550000, false});
  out->push_back(CarrierTableRow{"C395", "IUWG", "Carrier 395 Freight Systems", "LAX", 562500, true});
  out->push_back(CarrierTableRow{"C396", "PEOW", "Carrier 396 Freight Systems", "LAX", 575000, false});
  out->push_back(CarrierTableRow{"C397", "ZKPC", "Carrier 397 Freight Systems", "SLC", 587500, false});
  out->push_back(CarrierTableRow{"C398", "APLI", "Carrier 398 Freight Systems", "NSH", 600000, false});
  out->push_back(CarrierTableRow{"C399", "TITL", "Carrier 399 Freight Systems", "CHI", 612500, false});
  out->push_back(CarrierTableRow{"C400", "IKVZ", "Carrier 400 Freight Systems", "ATL", 625000, true});
  out->push_back(CarrierTableRow{"C401", "MPFP", "Carrier 401 Freight Systems", "DEN", 637500, false});
  out->push_back(CarrierTableRow{"C402", "ACFE", "Carrier 402 Freight Systems", "BOS", 650000, false});
  out->push_back(CarrierTableRow{"C403", "XZKJ", "Carrier 403 Freight Systems", "PDX", 662500, false});
  out->push_back(CarrierTableRow{"C404", "ARUW", "Carrier 404 Freight Systems", "YVR", 675000, false});
  out->push_back(CarrierTableRow{"C405", "UPNG", "Carrier 405 Freight Systems", "TPA", 687500, true});
  out->push_back(CarrierTableRow{"C406", "PPRR", "Carrier 406 Freight Systems", "STL", 700000, false});
  out->push_back(CarrierTableRow{"C407", "BKOT", "Carrier 407 Freight Systems", "CHI", 250000, false});
  out->push_back(CarrierTableRow{"C408", "FVJX", "Carrier 408 Freight Systems", "DTW", 262500, false});
  out->push_back(CarrierTableRow{"C409", "ZUCB", "Carrier 409 Freight Systems", "RNO", 275000, false});
  out->push_back(CarrierTableRow{"C410", "LXAM", "Carrier 410 Freight Systems", "YVR", 287500, true});
  out->push_back(CarrierTableRow{"C411", "IODB", "Carrier 411 Freight Systems", "JAX", 300000, false});
  out->push_back(CarrierTableRow{"C412", "ANOK", "Carrier 412 Freight Systems", "DEN", 312500, false});
  out->push_back(CarrierTableRow{"C413", "PHZV", "Carrier 413 Freight Systems", "YVR", 325000, false});
  out->push_back(CarrierTableRow{"C414", "OLFR", "Carrier 414 Freight Systems", "DEN", 337500, false});
  out->push_back(CarrierTableRow{"C415", "ZVXZ", "Carrier 415 Freight Systems", "IND", 350000, true});
  out->push_back(CarrierTableRow{"C416", "SZUA", "Carrier 416 Freight Systems", "PDX", 362500, false});
  out->push_back(CarrierTableRow{"C417", "QTLC", "Carrier 417 Freight Systems", "DEN", 375000, false});
  out->push_back(CarrierTableRow{"C418", "IFFW", "Carrier 418 Freight Systems", "DEN", 387500, false});
  out->push_back(CarrierTableRow{"C419", "ZOWA", "Carrier 419 Freight Systems", "CHI", 400000, false});
}

}  // namespace freight
