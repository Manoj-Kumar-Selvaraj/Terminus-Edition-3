package model

const (
	StatusPending   = "pending"
	StatusClaimed   = "claimed"
	StatusDelivered = "delivered"
	StatusFailed    = "failed"
	StatusDLQ       = "dlq"
)

const (
	OutcomeDelivered = "delivered"
	OutcomeFailed    = "failed"
)

const (
	ActionEnqueue     = "enqueue"
	ActionClaim       = "claim"
	ActionDeliverOK   = "deliver.ok"
	ActionDeliverFail = "deliver.fail"
	ActionDLQ         = "dlq"
	ActionReplay      = "replay"
	ActionPause       = "pause"
	ActionResume      = "resume"
)

func IsTerminal(status string) bool {
	switch status {
	case StatusDelivered, StatusDLQ:
		return true
	default:
		return false
	}
}

func ValidStatus(status string) bool {
	switch status {
	case StatusPending, StatusClaimed, StatusDelivered, StatusFailed, StatusDLQ:
		return true
	default:
		return false
	}
}

func CanClaimStatus(status string) bool {
	return status == StatusPending || status == StatusClaimed || status == StatusFailed
}
