package hashx

// Fletcher32 computes the fletcher32 checksum over raw bytes.
func Fletcher32(data []byte) uint64 {
	low := uint32(0)
	high := uint32(0)
	for i := 0; i < len(data); i += 2 {
		word := uint32(data[i])
		if i+1 < len(data) {
			word |= uint32(data[i+1]) << 8
		}
		low = (low + word) % 65535
		high = (high + low) % 65535
	}
	return uint64((high << 16) | low)
}
