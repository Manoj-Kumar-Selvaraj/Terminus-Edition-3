#include "freight/codecs.h"

namespace freight {

const std::vector<CodecAlgorithm>& codecRegistry() {
  static const std::vector<CodecAlgorithm> registry = {
      CodecAlgorithm{"hex_lower", &codec_encode_hex_lower, &codec_decode_hex_lower},
      CodecAlgorithm{"base32_rfc4648", &codec_encode_base32_rfc4648, &codec_decode_base32_rfc4648},
      CodecAlgorithm{"base64_std", &codec_encode_base64_std, &codec_decode_base64_std},
      CodecAlgorithm{"run_length", &codec_encode_run_length, &codec_decode_run_length},
      CodecAlgorithm{"delta_byte", &codec_encode_delta_byte, &codec_decode_delta_byte},
      CodecAlgorithm{"zigzag_byte", &codec_encode_zigzag_byte, &codec_decode_zigzag_byte},
      CodecAlgorithm{"uleb128_tagged", &codec_encode_uleb128_tagged, &codec_decode_uleb128_tagged},
      CodecAlgorithm{"escape_high", &codec_encode_escape_high, &codec_decode_escape_high},
      CodecAlgorithm{"quoted_freight", &codec_encode_quoted_freight, &codec_decode_quoted_freight},
      CodecAlgorithm{"nibble_split", &codec_encode_nibble_split, &codec_decode_nibble_split},
      CodecAlgorithm{"xor_pad8", &codec_encode_xor_pad8, &codec_decode_xor_pad8},
      CodecAlgorithm{"chunk16_framed", &codec_encode_chunk16_framed, &codec_decode_chunk16_framed},
  };
  return registry;
}

}  // namespace freight
