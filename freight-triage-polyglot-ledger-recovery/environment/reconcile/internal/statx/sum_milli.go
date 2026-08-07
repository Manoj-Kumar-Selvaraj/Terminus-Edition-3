package statx

// SumMilli is the sum_milli kernel.
func SumMilli(series []int64) int64 {
	total := int64(0)
	for _, value := range series {
		total += value
	}
	return total * 1000
}
