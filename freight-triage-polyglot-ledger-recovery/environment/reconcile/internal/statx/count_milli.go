package statx

// CountMilli is the count_milli kernel.
func CountMilli(series []int64) int64 {
	return int64(len(series)) * 1000
}
