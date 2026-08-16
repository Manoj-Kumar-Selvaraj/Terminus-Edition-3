package api

import (
	"errors"
	"net/http"

	"stackyard/internal/policy"
)

// mapPolicyError chooses an HTTP status for known policy failures.
func mapPolicyError(err error) int {
	switch {
	case errors.Is(err, policy.ErrNotLockHolder):
		return http.StatusForbidden
	case errors.Is(err, policy.ErrActiveRun),
		errors.Is(err, policy.ErrLockRequired),
		errors.Is(err, policy.ErrAlreadyLocked),
		errors.Is(err, policy.ErrInvalidTransition),
		errors.Is(err, policy.ErrWorkspaceBusy):
		return http.StatusConflict
	default:
		return http.StatusBadRequest
	}
}

// ErrorBody is the stable JSON error envelope from the contract.
type ErrorBody struct {
	Error string `json:"error"`
}
