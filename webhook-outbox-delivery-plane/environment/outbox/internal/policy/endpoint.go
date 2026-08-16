package policy

import (
	"errors"

	"outbox/internal/model"
)

var (
	ErrDisabled = errors.New("endpoint_disabled")
	ErrPaused   = errors.New("endpoint_unavailable")
)

func CanEnqueue(ep model.Endpoint) error {
	if !ep.Enabled {
		return ErrDisabled
	}
	return nil
}

func CanClaim(ep model.Endpoint) error {
	if !ep.Enabled || ep.Paused {
		return ErrPaused
	}
	return nil
}
