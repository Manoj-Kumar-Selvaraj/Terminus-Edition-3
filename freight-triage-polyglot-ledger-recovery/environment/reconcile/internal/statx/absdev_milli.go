package statx

// AbsdevMilli is the absdev_milli kernel.
func AbsdevMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	count := int64(len(series))
	total := int64(0)
	for _, value := range series {
		total += value
	}
	mean := FloorDiv(total*1000, count)
	accumulator := int64(0)
	for _, value := range series {
		delta := value*1000 - mean
		if delta < 0 {
			delta = -delta
		}
		accumulator += delta
	}
	return FloorDiv(accumulator, count)
}
