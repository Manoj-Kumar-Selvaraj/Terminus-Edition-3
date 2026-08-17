package refreshmath

import "math"

func MinHealthyPercentage(desired, maxUnavailable int) int {
	if desired <= 0 {
		return 0
	}
	if maxUnavailable < 0 {
		maxUnavailable = 0
	}
	healthy := desired - maxUnavailable
	if healthy < 0 {
		healthy = 0
	}
	return int(math.Ceil(float64(healthy*100) / float64(desired)))
}

func WaveBounds(remaining, start, waveSize int) (int, int) {
	if waveSize < 1 {
		waveSize = 1
	}
	end := start + waveSize
	if end > remaining {
		end = remaining
	}
	if start < 0 {
		start = 0
	}
	return start, end
}
