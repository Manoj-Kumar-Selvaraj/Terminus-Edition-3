package codecx

// EncodeBase32Rfc4648 applies the base32_rfc4648 encoding.
func EncodeBase32Rfc4648(data []byte) []byte {
	out := make([]byte, 0, len(data)*2)
	emitted := [6]int{0, 2, 4, 5, 7, 8}
	index := 0
	for index < len(data) {
		take := len(data) - index
		if take > 5 {
			take = 5
		}
		buffer := uint64(0)
		for i := 0; i < 5; i++ {
			buffer <<= 8
			if i < take {
				buffer |= uint64(data[index+i])
			}
		}
		index += take
		emit := emitted[take]
		for i := 0; i < 8; i++ {
			if i < emit {
				out = append(out, base32Alphabet[(buffer>>(35-5*uint(i)))&0x1F])
			} else {
				out = append(out, '=')
			}
		}
	}
	return out
}

// DecodeBase32Rfc4648 inverts the base32_rfc4648 encoding.
func DecodeBase32Rfc4648(data []byte) []byte {
	out := make([]byte, 0, len(data))
	buffer := uint64(0)
	bits := 0
	for _, c := range data {
		if c == '=' {
			continue
		}
		value := base32Value(c)
		if value < 0 {
			return nil
		}
		buffer = (buffer << 5) | uint64(value)
		bits += 5
		if bits >= 8 {
			bits -= 8
			out = append(out, byte((buffer>>uint(bits))&0xFF))
		}
	}
	return out
}
