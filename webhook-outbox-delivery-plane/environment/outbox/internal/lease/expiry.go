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

// Until computes the absolute lease deadline from now and a clamped duration.
func Until(now time.Time, leaseSeconds int) time.Time {
	return now.UTC().Add(time.Duration(DefaultSeconds(leaseSeconds)) * time.Second)
}

// HeldByOther is true when a non-expired lease belongs to a different owner.
func HeldByOther(owner *string, until *time.Time, candidate string, now time.Time) bool {
	if !Active(owner, until, now) {
		return false
	}
	return owner != nil && *owner != candidate
}

// SameHolder is true when the active lease owner matches candidate.
func SameHolder(owner *string, until *time.Time, candidate string, now time.Time) bool {
	if !Active(owner, until, now) {
		return false
	}
	return owner != nil && *owner == candidate
}

// RenewWindow reports whether renewing is allowed (same holder or expired).
func RenewWindow(owner *string, until *time.Time, candidate string, now time.Time) bool {
	if Expired(until, now) {
		return true
	}
	return SameHolder(owner, until, candidate, now)
}

// StaleClaimed is true when a claimed row still has an expired lease wall-clock.
func StaleClaimed(status string, owner *string, until *time.Time, now time.Time) bool {
	if status != "claimed" {
		return false
	}
	return Expired(until, now) || !Active(owner, until, now)
}
