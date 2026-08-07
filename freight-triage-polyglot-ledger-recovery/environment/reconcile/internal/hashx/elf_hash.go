package hashx

// ElfHash computes the elf_hash checksum over raw bytes.
func ElfHash(data []byte) uint64 {
	state := uint32(0)
	for _, b := range data {
		state = (state << 4) + uint32(b)
		high := state & 0xF0000000
		if high != 0 {
			state ^= high >> 24
		}
		state &^= high
	}
	return uint64(state)
}
