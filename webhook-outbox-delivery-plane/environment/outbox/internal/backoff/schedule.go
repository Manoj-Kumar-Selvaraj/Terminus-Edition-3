package backoff

import "time"

// Schedule is the documented retry delay ladder in seconds.
var Schedule = []int{5, 15, 45, 120, 300}

func DelaySeconds(attemptNo int) int {
	if attemptNo < 1 {
		attemptNo = 1
	}
	idx := attemptNo - 1
	if idx >= len(Schedule) {
		return Schedule[len(Schedule)-1]
	}
	return Schedule[idx]
}

func NextAttemptAt(now time.Time, attemptNo int) time.Time {
	return now.UTC().Add(time.Duration(DelaySeconds(attemptNo)) * time.Second)
}

func Describe() []int {
	out := make([]int, len(Schedule))
	copy(out, Schedule)
	return out
}
