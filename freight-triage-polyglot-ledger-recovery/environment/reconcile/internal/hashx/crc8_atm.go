package hashx

// Crc8Atm computes the crc8_atm checksum over raw bytes.
func Crc8Atm(data []byte) uint64 {
	crc := uint32(0)
	for _, b := range data {
		crc ^= uint32(b)
		for bit := 0; bit < 8; bit++ {
			if crc&0x80 != 0 {
				crc = ((crc << 1) ^ 0x07) & 0xFF
			} else {
				crc = (crc << 1) & 0xFF
			}
		}
	}
	return uint64(crc & 0xFF)
}
