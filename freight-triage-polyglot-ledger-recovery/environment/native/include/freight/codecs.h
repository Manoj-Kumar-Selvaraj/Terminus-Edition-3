#ifndef FREIGHT_CODECS_H
#define FREIGHT_CODECS_H

// Byte codec family. Each codec round-trips exactly and is mirrored in the
// Java and Go implementations.

#include <cstdint>
#include <string>
#include <vector>

namespace freight {

extern const uint8_t kXorPad[8];

int hexValue(char c);
int base32Value(char c);
int base64Value(char c);

std::string codec_encode_hex_lower(const std::string& data);
std::string codec_decode_hex_lower(const std::string& data);
std::string codec_encode_base32_rfc4648(const std::string& data);
std::string codec_decode_base32_rfc4648(const std::string& data);
std::string codec_encode_base64_std(const std::string& data);
std::string codec_decode_base64_std(const std::string& data);
std::string codec_encode_run_length(const std::string& data);
std::string codec_decode_run_length(const std::string& data);
std::string codec_encode_delta_byte(const std::string& data);
std::string codec_decode_delta_byte(const std::string& data);
std::string codec_encode_zigzag_byte(const std::string& data);
std::string codec_decode_zigzag_byte(const std::string& data);
std::string codec_encode_uleb128_tagged(const std::string& data);
std::string codec_decode_uleb128_tagged(const std::string& data);
std::string codec_encode_escape_high(const std::string& data);
std::string codec_decode_escape_high(const std::string& data);
std::string codec_encode_quoted_freight(const std::string& data);
std::string codec_decode_quoted_freight(const std::string& data);
std::string codec_encode_nibble_split(const std::string& data);
std::string codec_decode_nibble_split(const std::string& data);
std::string codec_encode_xor_pad8(const std::string& data);
std::string codec_decode_xor_pad8(const std::string& data);
std::string codec_encode_chunk16_framed(const std::string& data);
std::string codec_decode_chunk16_framed(const std::string& data);

struct CodecAlgorithm {
  const char* name;
  std::string (*encode)(const std::string& data);
  std::string (*decode)(const std::string& data);
};

const std::vector<CodecAlgorithm>& codecRegistry();

}  // namespace freight

#endif  // FREIGHT_CODECS_H
