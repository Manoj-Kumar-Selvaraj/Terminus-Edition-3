package statx

// MinMilli is the min_milli kernel.
func MinMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	best := series[0]
	for _, value := range series[1:] {
		if value < best {
			best = value
		}
	}
	return best * 1000
}
