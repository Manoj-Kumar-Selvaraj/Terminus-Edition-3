// Package statx holds fixed point windowed statistics. Results are scaled by
// one thousand and use floor division so every language agrees exactly.
package statx

// Kernel is a named statistic over an integer series.
type Kernel struct {
	Name  string
	Apply func(series []int64) int64
}

// FloorDiv divides rounding towards negative infinity.
func FloorDiv(numerator, denominator int64) int64 {
	if denominator == 0 {
		return 0
	}
	quotient := numerator / denominator
	remainder := numerator % denominator
	if remainder != 0 && ((remainder < 0) != (denominator < 0)) {
		quotient--
	}
	return quotient
}

// IntegerSqrt returns the floor of the square root of value.
func IntegerSqrt(value int64) int64 {
	if value <= 0 {
		return 0
	}
	low := int64(0)
	high := value
	if high > 3037000499 {
		high = 3037000499
	}
	for low < high {
		mid := low + (high-low+1)/2
		if mid <= value/mid {
			low = mid
		} else {
			high = mid - 1
		}
	}
	return low
}
