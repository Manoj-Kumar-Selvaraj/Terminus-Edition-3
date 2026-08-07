package hashx

// Crc32Ieee computes the crc32_ieee checksum over raw bytes.
func Crc32Ieee(data []byte) uint64 {
	crc := uint32(0xFFFFFFFF)
	for _, b := range data {
		crc ^= uint32(b)
		for bit := 0; bit < 8; bit++ {
			if crc&1 != 0 {
				crc = (crc >> 1) ^ 0xEDB88320
			} else {
				crc >>= 1
			}
		}
	}
	return uint64(crc ^ 0xFFFFFFFF)
}
