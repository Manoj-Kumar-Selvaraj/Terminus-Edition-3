package codecx

// EncodeQuotedFreight applies the quoted_freight encoding.
func EncodeQuotedFreight(data []byte) []byte {
	out := make([]byte, 0, len(data))
	for _, b := range data {
		if b >= 0x20 && b <= 0x7E && b != '=' {
			out = append(out, b)
			continue
		}
		out = append(out, '=', upperHex[b>>4], upperHex[b&0x0F])
	}
	return out
}

// DecodeQuotedFreight inverts the quoted_freight encoding.
func DecodeQuotedFreight(data []byte) []byte {
	out := make([]byte, 0, len(data))
	for i := 0; i < len(data); i++ {
		if data[i] != '=' {
			out = append(out, data[i])
			continue
		}
		if i+2 >= len(data) {
			break
		}
		high := hexValue(data[i+1])
		low := hexValue(data[i+2])
		if high < 0 || low < 0 {
			return nil
		}
		out = append(out, byte(high<<4|low))
		i += 2
	}
	return out
}
