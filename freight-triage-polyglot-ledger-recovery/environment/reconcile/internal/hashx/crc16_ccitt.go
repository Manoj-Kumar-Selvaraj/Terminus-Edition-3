package hashx

// Crc16Ccitt computes the crc16_ccitt checksum over raw bytes.
func Crc16Ccitt(data []byte) uint64 {
	crc := uint32(0xFFFF)
	for _, b := range data {
		crc ^= uint32(b) << 8
		for bit := 0; bit < 8; bit++ {
			if crc&0x8000 != 0 {
				crc = ((crc << 1) ^ 0x1021) & 0xFFFF
			} else {
				crc = (crc << 1) & 0xFFFF
			}
		}
	}
	return uint64(crc & 0xFFFF)
}
