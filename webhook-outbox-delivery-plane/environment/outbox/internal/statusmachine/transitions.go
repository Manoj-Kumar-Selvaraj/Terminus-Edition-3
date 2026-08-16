package statusmachine

import "outbox/internal/model"

// CanTransition reports whether a single status hop is legal for the outbox lifecycle.
func CanTransition(from, to string) bool {
	for _, t := range AllowedTargets(from) {
		if t == to {
			return true
		}
	}
	return false
}

// AllowedTargets lists legal next statuses from from.
func AllowedTargets(from string) []string {
	switch from {
	case model.StatusPending:
		return []string{model.StatusClaimed, model.StatusPending}
	case model.StatusClaimed:
		return []string{model.StatusDelivered, model.StatusPending, model.StatusDLQ, model.StatusClaimed}
	case model.StatusFailed:
		return []string{model.StatusPending, model.StatusClaimed, model.StatusDLQ}
	case model.StatusDLQ:
		return []string{model.StatusPending}
	case model.StatusDelivered:
		return nil
	default:
		return nil
	}
}

// AfterFailure chooses pending retry vs DLQ once attemptNo has been recorded.
func AfterFailure(attemptNo, maxAttempts int) string {
	if maxAttempts < 1 {
		maxAttempts = 1
	}
	if attemptNo < 1 {
		attemptNo = 1
	}
	if attemptNo >= maxAttempts {
		return model.StatusDLQ
	}
	return model.StatusPending
}

// AfterSuccess is always delivered when the prior status was claimable.
func AfterSuccess(from string) (string, bool) {
	if CanTransition(from, model.StatusDelivered) {
		return model.StatusDelivered, true
	}
	return "", false
}

// ClaimTarget is the status written when a worker takes a lease.
func ClaimTarget() string {
	return model.StatusClaimed
}

// ReplayTarget is the status written when an operator replays a DLQ event.
func ReplayTarget() string {
	return model.StatusPending
}

// ValidatePath checks a multi-hop path where each consecutive pair must be legal.
func ValidatePath(path []string) bool {
	if len(path) < 2 {
		return false
	}
	for i := 0; i < len(path)-1; i++ {
		if !CanTransition(path[i], path[i+1]) {
			return false
		}
	}
	return true
}

// IsAbsorbing reports terminal statuses that never leave without an explicit replay.
func IsAbsorbing(status string) bool {
	return status == model.StatusDelivered || status == model.StatusDLQ
}

// MustAllow returns an error string when the hop is illegal.
func MustAllow(from, to string) error {
	if CanTransition(from, to) {
		return nil
	}
	return errBadTransition{From: from, To: to}
}

type errBadTransition struct {
	From string
	To   string
}

func (e errBadTransition) Error() string {
	return "invalid_status"
}
