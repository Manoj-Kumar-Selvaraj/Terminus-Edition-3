#include "freight/formats.h"

namespace freight {

const std::vector<Formatter>& formatterRegistry() {
  static const std::vector<Formatter> registry = {
      Formatter{"kg_to_tonnes", &fmt_kg_to_tonnes},
      Formatter{"cents_to_amount", &fmt_cents_to_amount},
      Formatter{"lane_label", &fmt_lane_label},
      Formatter{"window_label", &fmt_window_label},
      Formatter{"duration_hms", &fmt_duration_hms},
      Formatter{"hex_dump8", &fmt_hex_dump8},
      Formatter{"percent_basis", &fmt_percent_basis},
      Formatter{"ordinal_suffix", &fmt_ordinal_suffix},
      Formatter{"thousands_group", &fmt_thousands_group},
      Formatter{"sign_prefix", &fmt_sign_prefix},
      Formatter{"slot_label", &fmt_slot_label},
      Formatter{"base36_upper", &fmt_base36_upper},
  };
  return registry;
}

}  // namespace freight
