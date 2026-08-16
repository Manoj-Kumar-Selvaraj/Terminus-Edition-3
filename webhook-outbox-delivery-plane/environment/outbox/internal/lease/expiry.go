package lease

import "time"

func Active(owner *string, until *time.Time, now time.Time) bool {
	if owner == nil || until == nil {
		return false
	}
	if *owner == "" {
		return false
	}
	return until.After(now.UTC())
}

func Expired(until *time.Time, now time.Time) bool {
	if until == nil {
		return true
	}
	return !until.After(now.UTC())
}

func Remaining(until *time.Time, now time.Time) time.Duration {
	if until == nil {
		return 0
	}
	d := until.Sub(now.UTC())
	if d < 0 {
		return 0
	}
	return d
}

func DefaultSeconds(n int) int {
	if n < 1 {
		return 30
	}
	if n > 3600 {
		return 3600
	}
	return n
}
