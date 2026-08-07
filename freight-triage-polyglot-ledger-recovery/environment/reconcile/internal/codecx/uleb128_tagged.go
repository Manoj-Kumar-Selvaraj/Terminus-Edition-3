package codecx

// EncodeUleb128Tagged applies the uleb128_tagged encoding.
func EncodeUleb128Tagged(data []byte) []byte {
	out := make([]byte, 0, len(data)*2)
	for _, b := range data {
		value := uint32(b)<<3 | uint32(b)&7
		for value >= 0x80 {
			out = append(out, byte(value&0x7F|0x80))
			value >>= 7
		}
		out = append(out, byte(value))
	}
	return out
}

// DecodeUleb128Tagged inverts the uleb128_tagged encoding.
func DecodeUleb128Tagged(data []byte) []byte {
	out := make([]byte, 0, len(data))
	value := uint32(0)
	shift := uint(0)
	for _, b := range data {
		value |= uint32(b&0x7F) << shift
		if b&0x80 != 0 {
			shift += 7
			continue
		}
		out = append(out, byte(value>>3))
		value = 0
		shift = 0
	}
	return out
}
