package hashx

// BsdSum16 computes the bsd_sum16 checksum over raw bytes.
func BsdSum16(data []byte) uint64 {
	state := uint32(0)
	for _, b := range data {
		state = ((state >> 1) | ((state & 1) << 15)) & 0xFFFF
		state = (state + uint32(b)) & 0xFFFF
	}
	return uint64(state)
}
