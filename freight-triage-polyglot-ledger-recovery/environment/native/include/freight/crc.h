#ifndef FREIGHT_CRC_H
#define FREIGHT_CRC_H

// CRC-32/ISO-HDLC (reflected, poly 0xEDB88320) used for freight seal digests.

#include <cstdint>
#include <string>

namespace freight {

uint32_t crc32Ieee(const std::string& data);
std::string sealDigestHex(const std::string& normalizedSeal);

}  // namespace freight

#endif  // FREIGHT_CRC_H
