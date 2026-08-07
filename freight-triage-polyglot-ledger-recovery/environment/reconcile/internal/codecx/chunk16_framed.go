package codecx

// EncodeChunk16Framed applies the chunk16_framed encoding.
func EncodeChunk16Framed(data []byte) []byte {
	out := make([]byte, 0, len(data)+len(data)/16+1)
	index := 0
	for index < len(data) {
		take := len(data) - index
		if take > 16 {
			take = 16
		}
		out = append(out, byte(take))
		out = append(out, data[index:index+take]...)
		index += take
	}
	return out
}

// DecodeChunk16Framed inverts the chunk16_framed encoding.
func DecodeChunk16Framed(data []byte) []byte {
	out := make([]byte, 0, len(data))
	index := 0
	for index < len(data) {
		take := int(data[index])
		index++
		if index+take > len(data) {
			take = len(data) - index
		}
		out = append(out, data[index:index+take]...)
		index += take
	}
	return out
}
