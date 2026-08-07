package statx

// RangeMilli is the range_milli kernel.
func RangeMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	low := series[0]
	high := series[0]
	for _, value := range series[1:] {
		if value < low {
			low = value
		}
		if value > high {
			high = value
		}
	}
	return (high - low) * 1000
}
