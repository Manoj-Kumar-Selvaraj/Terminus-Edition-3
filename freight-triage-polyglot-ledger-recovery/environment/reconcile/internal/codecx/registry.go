package codecx

// Registry lists every codec in catalogue order.
func Registry() []Codec {
	return []Codec{
		{Name: "hex_lower", Encode: EncodeHexLower, Decode: DecodeHexLower},
		{Name: "base32_rfc4648", Encode: EncodeBase32Rfc4648, Decode: DecodeBase32Rfc4648},
		{Name: "base64_std", Encode: EncodeBase64Std, Decode: DecodeBase64Std},
		{Name: "run_length", Encode: EncodeRunLength, Decode: DecodeRunLength},
		{Name: "delta_byte", Encode: EncodeDeltaByte, Decode: DecodeDeltaByte},
		{Name: "zigzag_byte", Encode: EncodeZigzagByte, Decode: DecodeZigzagByte},
		{Name: "uleb128_tagged", Encode: EncodeUleb128Tagged, Decode: DecodeUleb128Tagged},
		{Name: "escape_high", Encode: EncodeEscapeHigh, Decode: DecodeEscapeHigh},
		{Name: "quoted_freight", Encode: EncodeQuotedFreight, Decode: DecodeQuotedFreight},
		{Name: "nibble_split", Encode: EncodeNibbleSplit, Decode: DecodeNibbleSplit},
		{Name: "xor_pad8", Encode: EncodeXorPad8, Decode: DecodeXorPad8},
		{Name: "chunk16_framed", Encode: EncodeChunk16Framed, Decode: DecodeChunk16Framed},
	}
}
