package codecx

// EncodeBase64Std applies the base64_std encoding.
func EncodeBase64Std(data []byte) []byte {
	out := make([]byte, 0, len(data)*2)
	index := 0
	for index < len(data) {
		take := len(data) - index
		if take > 3 {
			take = 3
		}
		buffer := uint32(0)
		for i := 0; i < 3; i++ {
			buffer <<= 8
			if i < take {
				buffer |= uint32(data[index+i])
			}
		}
		index += take
		emit := take + 1
		for i := 0; i < 4; i++ {
			if i < emit {
				out = append(out, base64Alphabet[(buffer>>(18-6*uint(i)))&0x3F])
			} else {
				out = append(out, '=')
			}
		}
	}
	return out
}

// DecodeBase64Std inverts the base64_std encoding.
func DecodeBase64Std(data []byte) []byte {
	out := make([]byte, 0, len(data))
	buffer := uint32(0)
	bits := 0
	for _, c := range data {
		if c == '=' {
			continue
		}
		value := base64Value(c)
		if value < 0 {
			return nil
		}
		buffer = (buffer << 6) | uint32(value)
		bits += 6
		if bits >= 8 {
			bits -= 8
			out = append(out, byte((buffer>>uint(bits))&0xFF))
		}
	}
	return out
}
