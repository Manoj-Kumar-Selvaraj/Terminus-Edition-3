package hashx

// JenkinsOaat computes the jenkins_oaat checksum over raw bytes.
func JenkinsOaat(data []byte) uint64 {
	state := uint32(0)
	for _, b := range data {
		state += uint32(b)
		state += state << 10
		state ^= state >> 6
	}
	state += state << 3
	state ^= state >> 11
	state += state << 15
	return uint64(state)
}
