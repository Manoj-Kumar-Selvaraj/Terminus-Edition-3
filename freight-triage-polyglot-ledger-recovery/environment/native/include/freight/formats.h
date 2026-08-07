#ifndef FREIGHT_FORMATS_H
#define FREIGHT_FORMATS_H

// Display formatters used on dock sheets and audit exports. Each formatter
// is mirrored in the Java intake service and the Go reconciler.

#include <string>
#include <vector>

namespace freight {

std::string fmt_kg_to_tonnes(long long value);
std::string fmt_cents_to_amount(long long value);
std::string fmt_lane_label(long long value);
std::string fmt_window_label(long long value);
std::string fmt_duration_hms(long long value);
std::string fmt_hex_dump8(long long value);
std::string fmt_percent_basis(long long value);
std::string fmt_ordinal_suffix(long long value);
std::string fmt_thousands_group(long long value);
std::string fmt_sign_prefix(long long value);
std::string fmt_slot_label(long long value);
std::string fmt_base36_upper(long long value);

struct Formatter {
  const char* name;
  std::string (*apply)(long long value);
};

const std::vector<Formatter>& formatterRegistry();

}  // namespace freight

#endif  // FREIGHT_FORMATS_H
