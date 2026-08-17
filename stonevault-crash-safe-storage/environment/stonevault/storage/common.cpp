#include "common.hpp"

#include <algorithm>

namespace stonevault {

bool ByteLess::operator()(const std::string& lhs, const std::string& rhs) const noexcept {
    return std::lexicographical_compare(
        lhs.begin(), lhs.end(),
        rhs.begin(), rhs.end(),
        [](char a, char b) {
            return static_cast<unsigned char>(a) < static_cast<unsigned char>(b);
        });
}

}  // namespace stonevault
