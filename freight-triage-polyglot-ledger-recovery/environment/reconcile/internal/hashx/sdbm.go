package hashx

// Sdbm computes the sdbm checksum over raw bytes.
func Sdbm(data []byte) uint64 {
	state := uint32(0)
	for _, b := range data {
		state = uint32(b) + (state << 6) + (state << 16) - state
	}
	return uint64(state)
}
