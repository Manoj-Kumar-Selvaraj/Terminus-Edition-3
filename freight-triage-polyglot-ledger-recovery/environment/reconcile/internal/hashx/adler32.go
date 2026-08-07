package hashx

// Adler32 computes the adler32 checksum over raw bytes.
func Adler32(data []byte) uint64 {
	low := uint32(1)
	high := uint32(0)
	for _, b := range data {
		low = (low + uint32(b)) % 65521
		high = (high + low) % 65521
	}
	return uint64((high << 16) | low)
}
