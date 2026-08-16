package claim

import (
	"errors"
	"time"

	"outbox/internal/model"
	"outbox/internal/store"
)

var (
	ErrLeaseHeld     = errors.New("lease_held")
	ErrLeaseMismatch = errors.New("lease_mismatch")
	ErrUnavailable   = errors.New("endpoint_unavailable")
	ErrBadStatus     = errors.New("invalid_status")
)

type Service struct {
	Store *store.Store
}

func (s *Service) Acquire(ev model.Event, ep model.Endpoint, owner string, leaseSeconds int, now time.Time) (model.Event, error) {
	if !ep.Enabled || ep.Paused {
		return model.Event{}, ErrUnavailable
	}
	if !model.CanClaimStatus(ev.Status) && ev.Status != model.StatusClaimed {
		return model.Event{}, ErrBadStatus
	}
	if leaseSeconds < 1 {
		leaseSeconds = 30
	}
	until := now.UTC().Add(time.Duration(leaseSeconds) * time.Second)

	if ev.LeaseOwner != nil && ev.LeaseUntil != nil && ev.LeaseUntil.After(now) && *ev.LeaseOwner != owner {
		return model.Event{}, ErrLeaseHeld
	}

	if err := s.Store.UpdateEventLease(ev.ID, owner, until, model.StatusClaimed); err != nil {
		return model.Event{}, err
	}
	return s.Store.GetEvent(ev.ID)
}

func (s *Service) AssertHolder(ev model.Event, owner string, now time.Time) error {
	if ev.LeaseOwner == nil || *ev.LeaseOwner != owner {
		return ErrLeaseMismatch
	}
	if ev.LeaseUntil != nil && ev.LeaseUntil.Before(now) {
		return ErrLeaseMismatch
	}
	return nil
}
