#ifndef FREIGHT_NORMALIZE_H
#define FREIGHT_NORMALIZE_H

// ASCII normalizers applied to inbound freight reference strings.

#include <string>
#include <vector>

namespace freight {

std::string norm_upper_ascii(const std::string& text);
std::string norm_lower_ascii(const std::string& text);
std::string norm_trim_edges(const std::string& text);
std::string norm_collapse_spaces(const std::string& text);
std::string norm_strip_non_alnum(const std::string& text);
std::string norm_dash_to_underscore(const std::string& text);
std::string norm_pad_left_eight(const std::string& text);
std::string norm_reverse_bytes(const std::string& text);
std::string norm_rot13_letters(const std::string& text);
std::string norm_digits_only(const std::string& text);

struct Normalizer {
  const char* name;
  std::string (*apply)(const std::string& text);
};

const std::vector<Normalizer>& normalizerRegistry();

}  // namespace freight

#endif  // FREIGHT_NORMALIZE_H
