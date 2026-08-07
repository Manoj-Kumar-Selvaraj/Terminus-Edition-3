package hashx

// XorRotate computes the xor_rotate checksum over raw bytes.
func XorRotate(data []byte) uint64 {
	state := uint32(0)
	for _, b := range data {
		state = ((state << 5) | (state >> 27)) ^ uint32(b)
	}
	return uint64(state)
}
