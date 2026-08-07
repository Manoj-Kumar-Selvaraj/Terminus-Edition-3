package statx

// MaxMilli is the max_milli kernel.
func MaxMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	best := series[0]
	for _, value := range series[1:] {
		if value > best {
			best = value
		}
	}
	return best * 1000
}
