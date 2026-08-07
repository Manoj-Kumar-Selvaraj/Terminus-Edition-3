package statx

// StddevMilli is the stddev_milli kernel.
func StddevMilli(series []int64) int64 {
	return IntegerSqrt(VarianceMilli(series) * 1000)
}
