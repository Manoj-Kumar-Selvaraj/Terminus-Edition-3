package model

// StatusRank provides a coarse ordering used when summarizing run histories.
func StatusRank(status string) int {
	switch status {
	case StatusQueued:
		return 10
	case StatusRunning:
		return 20
	case StatusPlanned:
		return 30
	case StatusApplied:
		return 40
	case StatusErrored:
		return 50
	case StatusDiscarded:
		return 60
	case StatusCanceled:
		return 70
	default:
		return 0
	}
}

// ValidateCommand reports whether command is one of the supported Stackyard ops.
func ValidateCommand(command string) bool {
	return AllowedCommands[command]
}

// ValidateCategory reports whether category is terraform or env.
func ValidateCategory(category string) bool {
	return category == CategoryTerraform || category == CategoryEnv
}

// AuditActions lists the stable audit action vocabulary from the contract.
func AuditActions() []string {
	return []string{
		AuditRunCreated,
		AuditRunStatus,
		AuditLockAcquire,
		AuditLockRelease,
	}
}
