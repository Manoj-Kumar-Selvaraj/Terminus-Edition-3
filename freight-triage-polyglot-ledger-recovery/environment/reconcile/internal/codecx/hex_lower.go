package codecx

// EncodeHexLower applies the hex_lower encoding.
func EncodeHexLower(data []byte) []byte {
	out := make([]byte, 0, len(data)*2)
	for _, b := range data {
		out = append(out, hexDigits[b>>4], hexDigits[b&0x0F])
	}
	return out
}

// DecodeHexLower inverts the hex_lower encoding.
func DecodeHexLower(data []byte) []byte {
	out := make([]byte, 0, len(data)/2)
	for i := 0; i+1 < len(data); i += 2 {
		high := hexValue(data[i])
		low := hexValue(data[i+1])
		if high < 0 || low < 0 {
			return nil
		}
		out = append(out, byte(high<<4|low))
	}
	return out
}
