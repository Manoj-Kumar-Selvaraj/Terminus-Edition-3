package statx

// EwmaMilli is the ewma_milli kernel.
func EwmaMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	state := series[0] * 1000
	for _, value := range series[1:] {
		state += FloorDiv(value*1000-state, 4)
	}
	return state
}
