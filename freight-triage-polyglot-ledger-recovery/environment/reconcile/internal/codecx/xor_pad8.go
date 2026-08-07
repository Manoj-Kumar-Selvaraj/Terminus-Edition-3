package codecx

// EncodeXorPad8 applies the xor_pad8 encoding.
func EncodeXorPad8(data []byte) []byte {
	out := make([]byte, len(data))
	for i, b := range data {
		out[i] = b ^ xorPad[i%8]
	}
	return out
}

// DecodeXorPad8 inverts the xor_pad8 encoding.
func DecodeXorPad8(data []byte) []byte {
	out := make([]byte, len(data))
	for i, b := range data {
		out[i] = b ^ xorPad[i%8]
	}
	return out
}
