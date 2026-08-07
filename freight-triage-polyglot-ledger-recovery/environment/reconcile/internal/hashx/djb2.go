package hashx

// Djb2 computes the djb2 checksum over raw bytes.
func Djb2(data []byte) uint64 {
	state := uint32(5381)
	for _, b := range data {
		state = state*33 + uint32(b)
	}
	return uint64(state)
}
