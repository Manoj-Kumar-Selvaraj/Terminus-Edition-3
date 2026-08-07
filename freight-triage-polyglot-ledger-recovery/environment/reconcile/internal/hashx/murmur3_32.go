package hashx

// Murmur332 computes the murmur3_32 checksum over raw bytes.
func Murmur332(data []byte) uint64 {
	state := uint32(0x5F3A1C7D)
	blocks := len(data) / 4
	for i := 0; i < blocks; i++ {
		k := uint32(data[i*4]) | uint32(data[i*4+1])<<8 | uint32(data[i*4+2])<<16 |
			uint32(data[i*4+3])<<24
		k *= 0xCC9E2D51
		k = (k << 15) | (k >> 17)
		k *= 0x1B873593
		state ^= k
		state = (state << 13) | (state >> 19)
		state = state*5 + 0xE6546B64
	}
	tail := uint32(0)
	remainder := len(data) & 3
	if remainder >= 3 {
		tail ^= uint32(data[blocks*4+2]) << 16
	}
	if remainder >= 2 {
		tail ^= uint32(data[blocks*4+1]) << 8
	}
	if remainder >= 1 {
		tail ^= uint32(data[blocks*4])
		tail *= 0xCC9E2D51
		tail = (tail << 15) | (tail >> 17)
		tail *= 0x1B873593
		state ^= tail
	}
	state ^= uint32(len(data))
	state ^= state >> 16
	state *= 0x85EBCA6B
	state ^= state >> 13
	state *= 0xC2B2AE35
	state ^= state >> 16
	return uint64(state)
}
