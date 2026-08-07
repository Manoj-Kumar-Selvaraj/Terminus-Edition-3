package statx

import "sort"

// P90Milli is the p90_milli kernel.
func P90Milli(series []int64) int64 {
	if len(series) == 0 {
		return 0
	}
	sorted := make([]int64, len(series))
	copy(sorted, series)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	count := int64(len(sorted))
	rank := (9*count + 9) / 10
	if rank < 1 {
		rank = 1
	}
	if rank > count {
		rank = count
	}
	return sorted[rank-1] * 1000
}
