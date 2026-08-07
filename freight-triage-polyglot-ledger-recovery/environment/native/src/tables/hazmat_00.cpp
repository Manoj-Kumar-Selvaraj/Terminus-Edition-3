#include "freight/tables.h"

namespace freight {

// hazmat table rows 0..59.
void hazmatTableFill00(std::vector<HazmatTableRow>* out) {
  out->push_back(HazmatTableRow{"HZ-00", 0, 0, "S00", 4000});
  out->push_back(HazmatTableRow{"HZ-01", 1, 1, "S13", 4900});
  out->push_back(HazmatTableRow{"HZ-02", 2, 2, "S26", 5800});
  out->push_back(HazmatTableRow{"HZ-03", 3, 3, "S32", 6700});
  out->push_back(HazmatTableRow{"HZ-04", 4, 4, "S45", 7600});
  out->push_back(HazmatTableRow{"HZ-05", 5, 0, "S51", 8500});
  out->push_back(HazmatTableRow{"HZ-06", 6, 1, "S64", 9400});
  out->push_back(HazmatTableRow{"HZ-07", 7, 2, "S00", 10300});
  out->push_back(HazmatTableRow{"HZ-08", 8, 3, "S13", 11200});
  out->push_back(HazmatTableRow{"HZ-09", 0, 4, "S26", 12100});
  out->push_back(HazmatTableRow{"HZ-10", 1, 0, "S32", 13000});
  out->push_back(HazmatTableRow{"HZ-11", 2, 1, "S45", 13900});
  out->push_back(HazmatTableRow{"HZ-12", 3, 2, "S51", 14800});
  out->push_back(HazmatTableRow{"HZ-13", 4, 3, "S64", 4000});
  out->push_back(HazmatTableRow{"HZ-14", 5, 4, "S00", 4900});
  out->push_back(HazmatTableRow{"HZ-15", 6, 0, "S13", 5800});
  out->push_back(HazmatTableRow{"HZ-16", 7, 1, "S26", 6700});
  out->push_back(HazmatTableRow{"HZ-17", 8, 2, "S32", 7600});
  out->push_back(HazmatTableRow{"HZ-18", 0, 3, "S45", 8500});
  out->push_back(HazmatTableRow{"HZ-19", 1, 4, "S51", 9400});
  out->push_back(HazmatTableRow{"HZ-20", 2, 0, "S64", 10300});
  out->push_back(HazmatTableRow{"HZ-21", 3, 1, "S00", 11200});
  out->push_back(HazmatTableRow{"HZ-22", 4, 2, "S13", 12100});
  out->push_back(HazmatTableRow{"HZ-23", 5, 3, "S26", 13000});
  out->push_back(HazmatTableRow{"HZ-24", 6, 4, "S32", 13900});
  out->push_back(HazmatTableRow{"HZ-25", 7, 0, "S45", 14800});
  out->push_back(HazmatTableRow{"HZ-26", 8, 1, "S51", 4000});
  out->push_back(HazmatTableRow{"HZ-27", 0, 2, "S64", 4900});
  out->push_back(HazmatTableRow{"HZ-28", 1, 3, "S00", 5800});
  out->push_back(HazmatTableRow{"HZ-29", 2, 4, "S13", 6700});
  out->push_back(HazmatTableRow{"HZ-30", 3, 0, "S26", 7600});
  out->push_back(HazmatTableRow{"HZ-31", 4, 1, "S32", 8500});
  out->push_back(HazmatTableRow{"HZ-32", 5, 2, "S45", 9400});
  out->push_back(HazmatTableRow{"HZ-33", 6, 3, "S51", 10300});
  out->push_back(HazmatTableRow{"HZ-34", 7, 4, "S64", 11200});
  out->push_back(HazmatTableRow{"HZ-35", 8, 0, "S00", 12100});
  out->push_back(HazmatTableRow{"HZ-36", 0, 1, "S13", 13000});
  out->push_back(HazmatTableRow{"HZ-37", 1, 2, "S26", 13900});
  out->push_back(HazmatTableRow{"HZ-38", 2, 3, "S32", 14800});
  out->push_back(HazmatTableRow{"HZ-39", 3, 4, "S45", 4000});
  out->push_back(HazmatTableRow{"HZ-40", 4, 0, "S51", 4900});
  out->push_back(HazmatTableRow{"HZ-41", 5, 1, "S64", 5800});
  out->push_back(HazmatTableRow{"HZ-42", 6, 2, "S00", 6700});
  out->push_back(HazmatTableRow{"HZ-43", 7, 3, "S13", 7600});
  out->push_back(HazmatTableRow{"HZ-44", 8, 4, "S26", 8500});
  out->push_back(HazmatTableRow{"HZ-45", 0, 0, "S32", 9400});
  out->push_back(HazmatTableRow{"HZ-46", 1, 1, "S45", 10300});
  out->push_back(HazmatTableRow{"HZ-47", 2, 2, "S51", 11200});
  out->push_back(HazmatTableRow{"HZ-48", 3, 3, "S64", 12100});
  out->push_back(HazmatTableRow{"HZ-49", 4, 4, "S00", 13000});
  out->push_back(HazmatTableRow{"HZ-50", 5, 0, "S13", 13900});
  out->push_back(HazmatTableRow{"HZ-51", 6, 1, "S26", 14800});
  out->push_back(HazmatTableRow{"HZ-52", 7, 2, "S32", 4000});
  out->push_back(HazmatTableRow{"HZ-53", 8, 3, "S45", 4900});
  out->push_back(HazmatTableRow{"HZ-54", 0, 4, "S51", 5800});
  out->push_back(HazmatTableRow{"HZ-55", 1, 0, "S64", 6700});
  out->push_back(HazmatTableRow{"HZ-56", 2, 1, "S00", 7600});
  out->push_back(HazmatTableRow{"HZ-57", 3, 2, "S13", 8500});
  out->push_back(HazmatTableRow{"HZ-58", 4, 3, "S26", 9400});
  out->push_back(HazmatTableRow{"HZ-59", 5, 4, "S32", 10300});
}

}  // namespace freight
