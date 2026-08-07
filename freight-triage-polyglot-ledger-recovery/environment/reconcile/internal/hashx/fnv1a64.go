package hashx

// Fnv1a64 computes the fnv1a64 checksum over raw bytes.
func Fnv1a64(data []byte) uint64 {
	state := uint64(14695981039346656037)
	for _, b := range data {
		state ^= uint64(b)
		state *= 1099511628211
	}
	return state
}
