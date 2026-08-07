package hashx

// Crc32c computes the crc32c checksum over raw bytes.
func Crc32c(data []byte) uint64 {
	crc := uint32(0xFFFFFFFF)
	for _, b := range data {
		crc ^= uint32(b)
		for bit := 0; bit < 8; bit++ {
			if crc&1 != 0 {
				crc = (crc >> 1) ^ 0x82F63B78
			} else {
				crc >>= 1
			}
		}
	}
	return uint64(crc ^ 0xFFFFFFFF)
}
