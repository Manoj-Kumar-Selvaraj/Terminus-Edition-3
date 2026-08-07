#include "freight/tables.h"

namespace freight {

// tariff table rows 0..59.
void tariffTableFill00(std::vector<TariffTableRow>* out) {
  out->push_back(TariffTableRow{"G00", "B0", 400});
  out->push_back(TariffTableRow{"G00", "B1", 491});
  out->push_back(TariffTableRow{"G00", "B2", 582});
  out->push_back(TariffTableRow{"G00", "B3", 673});
  out->push_back(TariffTableRow{"G00", "B4", 764});
  out->push_back(TariffTableRow{"G00", "B5", 855});
  out->push_back(TariffTableRow{"G00", "B6", 946});
  out->push_back(TariffTableRow{"G00", "B7", 1037});
  out->push_back(TariffTableRow{"G01", "B0", 437});
  out->push_back(TariffTableRow{"G01", "B1", 541});
  out->push_back(TariffTableRow{"G01", "B2", 645});
  out->push_back(TariffTableRow{"G01", "B3", 749});
  out->push_back(TariffTableRow{"G01", "B4", 853});
  out->push_back(TariffTableRow{"G01", "B5", 900});
  out->push_back(TariffTableRow{"G01", "B6", 1004});
  out->push_back(TariffTableRow{"G01", "B7", 1108});
  out->push_back(TariffTableRow{"G02", "B0", 474});
  out->push_back(TariffTableRow{"G02", "B1", 591});
  out->push_back(TariffTableRow{"G02", "B2", 708});
  out->push_back(TariffTableRow{"G02", "B3", 768});
  out->push_back(TariffTableRow{"G02", "B4", 885});
  out->push_back(TariffTableRow{"G02", "B5", 945});
  out->push_back(TariffTableRow{"G02", "B6", 1062});
  out->push_back(TariffTableRow{"G02", "B7", 1122});
  out->push_back(TariffTableRow{"G03", "B0", 511});
  out->push_back(TariffTableRow{"G03", "B1", 641});
  out->push_back(TariffTableRow{"G03", "B2", 714});
  out->push_back(TariffTableRow{"G03", "B3", 787});
  out->push_back(TariffTableRow{"G03", "B4", 917});
  out->push_back(TariffTableRow{"G03", "B5", 990});
  out->push_back(TariffTableRow{"G03", "B6", 1063});
  out->push_back(TariffTableRow{"G03", "B7", 1193});
  out->push_back(TariffTableRow{"G04", "B0", 548});
  out->push_back(TariffTableRow{"G04", "B1", 691});
  out->push_back(TariffTableRow{"G04", "B2", 777});
  out->push_back(TariffTableRow{"G04", "B3", 863});
  out->push_back(TariffTableRow{"G04", "B4", 949});
  out->push_back(TariffTableRow{"G04", "B5", 1035});
  out->push_back(TariffTableRow{"G04", "B6", 1121});
  out->push_back(TariffTableRow{"G04", "B7", 1207});
  out->push_back(TariffTableRow{"G05", "B0", 585});
  out->push_back(TariffTableRow{"G05", "B1", 684});
  out->push_back(TariffTableRow{"G05", "B2", 783});
  out->push_back(TariffTableRow{"G05", "B3", 882});
  out->push_back(TariffTableRow{"G05", "B4", 981});
  out->push_back(TariffTableRow{"G05", "B5", 1080});
  out->push_back(TariffTableRow{"G05", "B6", 1179});
  out->push_back(TariffTableRow{"G05", "B7", 1278});
  out->push_back(TariffTableRow{"G06", "B0", 622});
  out->push_back(TariffTableRow{"G06", "B1", 734});
  out->push_back(TariffTableRow{"G06", "B2", 846});
  out->push_back(TariffTableRow{"G06", "B3", 901});
  out->push_back(TariffTableRow{"G06", "B4", 1013});
  out->push_back(TariffTableRow{"G06", "B5", 1125});
  out->push_back(TariffTableRow{"G06", "B6", 1180});
  out->push_back(TariffTableRow{"G06", "B7", 1292});
  out->push_back(TariffTableRow{"G07", "B0", 659});
  out->push_back(TariffTableRow{"G07", "B1", 784});
  out->push_back(TariffTableRow{"G07", "B2", 852});
  out->push_back(TariffTableRow{"G07", "B3", 977});
}

}  // namespace freight
