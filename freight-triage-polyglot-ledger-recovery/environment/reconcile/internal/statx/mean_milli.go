package statx

// MeanMilli is the mean_milli kernel.
func MeanMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	total := int64(0)
	for _, value := range series {
		total += value
	}
	return FloorDiv(total*1000, int64(len(series)))
}
