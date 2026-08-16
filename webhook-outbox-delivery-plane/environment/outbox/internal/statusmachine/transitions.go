package statusmachine

import "outbox/internal/model"

func CanTransition(from, to string) bool {
	switch from {
	case model.StatusPending:
		return to == model.StatusClaimed || to == model.StatusPending
	case model.StatusClaimed:
		return to == model.StatusDelivered || to == model.StatusPending || to == model.StatusDLQ || to == model.StatusClaimed
	case model.StatusFailed:
		return to == model.StatusPending || to == model.StatusClaimed || to == model.StatusDLQ
	case model.StatusDLQ:
		return to == model.StatusPending
	case model.StatusDelivered:
		return false
	default:
		return false
	}
}

func AfterFailure(attemptNo, maxAttempts int) string {
	if attemptNo >= maxAttempts {
		return model.StatusDLQ
	}
	return model.StatusPending
}
