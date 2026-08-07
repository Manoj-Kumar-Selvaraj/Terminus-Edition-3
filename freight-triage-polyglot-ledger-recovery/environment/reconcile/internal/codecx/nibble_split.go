package codecx

// EncodeNibbleSplit applies the nibble_split encoding.
func EncodeNibbleSplit(data []byte) []byte {
	out := make([]byte, len(data)*2)
	for i, b := range data {
		out[i*2] = 'A' + (b >> 4)
		out[i*2+1] = 'a' + (b & 0x0F)
	}
	return out
}

// DecodeNibbleSplit inverts the nibble_split encoding.
func DecodeNibbleSplit(data []byte) []byte {
	out := make([]byte, 0, len(data)/2)
	for i := 0; i+1 < len(data); i += 2 {
		high := data[i] - 'A'
		low := data[i+1] - 'a'
		out = append(out, (high<<4)|(low&0x0F))
	}
	return out
}
