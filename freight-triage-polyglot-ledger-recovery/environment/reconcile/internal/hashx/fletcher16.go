package hashx

// Fletcher16 computes the fletcher16 checksum over raw bytes.
func Fletcher16(data []byte) uint64 {
	low := uint32(0)
	high := uint32(0)
	for _, b := range data {
		low = (low + uint32(b)) % 255
		high = (high + low) % 255
	}
	return uint64((high << 8) | low)
}
