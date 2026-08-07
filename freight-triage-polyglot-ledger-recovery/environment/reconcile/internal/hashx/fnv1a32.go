package hashx

// Fnv1a32 computes the fnv1a32 checksum over raw bytes.
func Fnv1a32(data []byte) uint64 {
	state := uint32(2166136261)
	for _, b := range data {
		state ^= uint32(b)
		state *= 16777619
	}
	return uint64(state)
}
