package claim

import (
	"errors"
	"time"

	"outbox/internal/lease"
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
	leaseSeconds = lease.DefaultSeconds(leaseSeconds)
	until := lease.Until(now, leaseSeconds)

	if lease.HeldByOther(ev.LeaseOwner, ev.LeaseUntil, owner, now) {
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
	if ev.LeaseUntil != nil && lease.Expired(ev.LeaseUntil, now) {
		return ErrLeaseMismatch
	}
	return nil
}

func FenceBlocks(ev model.Event, owner string, now time.Time) bool {
	return lease.HeldByOther(ev.LeaseOwner, ev.LeaseUntil, owner, now)
}

func RenewAllowed(ev model.Event, owner string, now time.Time) bool {
	return lease.RenewWindow(ev.LeaseOwner, ev.LeaseUntil, owner, now)
}
