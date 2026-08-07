#include "freight/tables.h"

namespace freight {

// tariff table rows 60..95.
void tariffTableFill01(std::vector<TariffTableRow>* out) {
  out->push_back(TariffTableRow{"G07", "B4", 1045});
  out->push_back(TariffTableRow{"G07", "B5", 1170});
  out->push_back(TariffTableRow{"G07", "B6", 1238});
  out->push_back(TariffTableRow{"G07", "B7", 1306});
  out->push_back(TariffTableRow{"G08", "B0", 696});
  out->push_back(TariffTableRow{"G08", "B1", 834});
  out->push_back(TariffTableRow{"G08", "B2", 915});
  out->push_back(TariffTableRow{"G08", "B3", 996});
  out->push_back(TariffTableRow{"G08", "B4", 1077});
  out->push_back(TariffTableRow{"G08", "B5", 1158});
  out->push_back(TariffTableRow{"G08", "B6", 1296});
  out->push_back(TariffTableRow{"G08", "B7", 1377});
  out->push_back(TariffTableRow{"G09", "B0", 733});
  out->push_back(TariffTableRow{"G09", "B1", 827});
  out->push_back(TariffTableRow{"G09", "B2", 921});
  out->push_back(TariffTableRow{"G09", "B3", 1015});
  out->push_back(TariffTableRow{"G09", "B4", 1109});
  out->push_back(TariffTableRow{"G09", "B5", 1203});
  out->push_back(TariffTableRow{"G09", "B6", 1297});
  out->push_back(TariffTableRow{"G09", "B7", 1391});
  out->push_back(TariffTableRow{"G10", "B0", 770});
  out->push_back(TariffTableRow{"G10", "B1", 877});
  out->push_back(TariffTableRow{"G10", "B2", 984});
  out->push_back(TariffTableRow{"G10", "B3", 1091});
  out->push_back(TariffTableRow{"G10", "B4", 1141});
  out->push_back(TariffTableRow{"G10", "B5", 1248});
  out->push_back(TariffTableRow{"G10", "B6", 1355});
  out->push_back(TariffTableRow{"G10", "B7", 1462});
  out->push_back(TariffTableRow{"G11", "B0", 807});
  out->push_back(TariffTableRow{"G11", "B1", 927});
  out->push_back(TariffTableRow{"G11", "B2", 990});
  out->push_back(TariffTableRow{"G11", "B3", 1110});
  out->push_back(TariffTableRow{"G11", "B4", 1173});
  out->push_back(TariffTableRow{"G11", "B5", 1293});
  out->push_back(TariffTableRow{"G11", "B6", 1356});
  out->push_back(TariffTableRow{"G11", "B7", 1476});
}

}  // namespace freight
