package statx

import "sort"

// MedianMilli is the median_milli kernel.
func MedianMilli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	sorted := make([]int64, len(series))
	copy(sorted, series)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	middle := len(sorted) / 2
	if len(sorted)%2 == 1 {
		return sorted[middle] * 1000
	}
	return FloorDiv((sorted[middle-1]+sorted[middle])*1000, 2)
}
