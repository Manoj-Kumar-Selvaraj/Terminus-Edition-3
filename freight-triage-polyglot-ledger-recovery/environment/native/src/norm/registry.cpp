#include "freight/normalize.h"

namespace freight {

const std::vector<Normalizer>& normalizerRegistry() {
  static const std::vector<Normalizer> registry = {
      Normalizer{"upper_ascii", &norm_upper_ascii},
      Normalizer{"lower_ascii", &norm_lower_ascii},
      Normalizer{"trim_edges", &norm_trim_edges},
      Normalizer{"collapse_spaces", &norm_collapse_spaces},
      Normalizer{"strip_non_alnum", &norm_strip_non_alnum},
      Normalizer{"dash_to_underscore", &norm_dash_to_underscore},
      Normalizer{"pad_left_eight", &norm_pad_left_eight},
      Normalizer{"reverse_bytes", &norm_reverse_bytes},
      Normalizer{"rot13_letters", &norm_rot13_letters},
      Normalizer{"digits_only", &norm_digits_only},
  };
  return registry;
}

}  // namespace freight
