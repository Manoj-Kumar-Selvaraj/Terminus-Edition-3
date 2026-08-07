#include "freight/tables.h"

namespace freight {

// hazmat table rows 60..119.
void hazmatTableFill01(std::vector<HazmatTableRow>* out) {
  out->push_back(HazmatTableRow{"HZ-60", 6, 0, "S45", 11200});
  out->push_back(HazmatTableRow{"HZ-61", 7, 1, "S51", 12100});
  out->push_back(HazmatTableRow{"HZ-62", 8, 2, "S64", 13000});
  out->push_back(HazmatTableRow{"HZ-63", 0, 3, "S00", 13900});
  out->push_back(HazmatTableRow{"HZ-64", 1, 4, "S13", 14800});
  out->push_back(HazmatTableRow{"HZ-65", 2, 0, "S26", 4000});
  out->push_back(HazmatTableRow{"HZ-66", 3, 1, "S32", 4900});
  out->push_back(HazmatTableRow{"HZ-67", 4, 2, "S45", 5800});
  out->push_back(HazmatTableRow{"HZ-68", 5, 3, "S51", 6700});
  out->push_back(HazmatTableRow{"HZ-69", 6, 4, "S64", 7600});
  out->push_back(HazmatTableRow{"HZ-70", 7, 0, "S00", 8500});
  out->push_back(HazmatTableRow{"HZ-71", 8, 1, "S13", 9400});
  out->push_back(HazmatTableRow{"HZ-72", 0, 2, "S26", 10300});
  out->push_back(HazmatTableRow{"HZ-73", 1, 3, "S32", 11200});
  out->push_back(HazmatTableRow{"HZ-74", 2, 4, "S45", 12100});
  out->push_back(HazmatTableRow{"HZ-75", 3, 0, "S51", 13000});
  out->push_back(HazmatTableRow{"HZ-76", 4, 1, "S64", 13900});
  out->push_back(HazmatTableRow{"HZ-77", 5, 2, "S00", 14800});
  out->push_back(HazmatTableRow{"HZ-78", 6, 3, "S13", 4000});
  out->push_back(HazmatTableRow{"HZ-79", 7, 4, "S26", 4900});
  out->push_back(HazmatTableRow{"HZ-80", 8, 0, "S32", 5800});
  out->push_back(HazmatTableRow{"HZ-81", 0, 1, "S45", 6700});
  out->push_back(HazmatTableRow{"HZ-82", 1, 2, "S51", 7600});
  out->push_back(HazmatTableRow{"HZ-83", 2, 3, "S64", 8500});
  out->push_back(HazmatTableRow{"HZ-84", 3, 4, "S00", 9400});
  out->push_back(HazmatTableRow{"HZ-85", 4, 0, "S13", 10300});
  out->push_back(HazmatTableRow{"HZ-86", 5, 1, "S26", 11200});
  out->push_back(HazmatTableRow{"HZ-87", 6, 2, "S32", 12100});
  out->push_back(HazmatTableRow{"HZ-88", 7, 3, "S45", 13000});
  out->push_back(HazmatTableRow{"HZ-89", 8, 4, "S51", 13900});
  out->push_back(HazmatTableRow{"HZ-90", 0, 0, "S64", 14800});
  out->push_back(HazmatTableRow{"HZ-91", 1, 1, "S00", 4000});
  out->push_back(HazmatTableRow{"HZ-92", 2, 2, "S13", 4900});
  out->push_back(HazmatTableRow{"HZ-93", 3, 3, "S26", 5800});
  out->push_back(HazmatTableRow{"HZ-94", 4, 4, "S32", 6700});
  out->push_back(HazmatTableRow{"HZ-95", 5, 0, "S45", 7600});
  out->push_back(HazmatTableRow{"HZ-96", 6, 1, "S51", 8500});
  out->push_back(HazmatTableRow{"HZ-97", 7, 2, "S64", 9400});
  out->push_back(HazmatTableRow{"HZ-98", 8, 3, "S00", 10300});
  out->push_back(HazmatTableRow{"HZ-99", 0, 4, "S13", 11200});
  out->push_back(HazmatTableRow{"HZ-100", 1, 0, "S26", 12100});
  out->push_back(HazmatTableRow{"HZ-101", 2, 1, "S32", 13000});
  out->push_back(HazmatTableRow{"HZ-102", 3, 2, "S45", 13900});
  out->push_back(HazmatTableRow{"HZ-103", 4, 3, "S51", 14800});
  out->push_back(HazmatTableRow{"HZ-104", 5, 4, "S64", 4000});
  out->push_back(HazmatTableRow{"HZ-105", 6, 0, "S00", 4900});
  out->push_back(HazmatTableRow{"HZ-106", 7, 1, "S13", 5800});
  out->push_back(HazmatTableRow{"HZ-107", 8, 2, "S26", 6700});
  out->push_back(HazmatTableRow{"HZ-108", 0, 3, "S32", 7600});
  out->push_back(HazmatTableRow{"HZ-109", 1, 4, "S45", 8500});
  out->push_back(HazmatTableRow{"HZ-110", 2, 0, "S51", 9400});
  out->push_back(HazmatTableRow{"HZ-111", 3, 1, "S64", 10300});
  out->push_back(HazmatTableRow{"HZ-112", 4, 2, "S00", 11200});
  out->push_back(HazmatTableRow{"HZ-113", 5, 3, "S13", 12100});
  out->push_back(HazmatTableRow{"HZ-114", 6, 4, "S26", 13000});
  out->push_back(HazmatTableRow{"HZ-115", 7, 0, "S32", 13900});
  out->push_back(HazmatTableRow{"HZ-116", 8, 1, "S45", 14800});
  out->push_back(HazmatTableRow{"HZ-117", 0, 2, "S51", 4000});
  out->push_back(HazmatTableRow{"HZ-118", 1, 3, "S64", 4900});
  out->push_back(HazmatTableRow{"HZ-119", 2, 4, "S00", 5800});
}

}  // namespace freight
