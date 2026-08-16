package quota

import (
	"errors"
	"time"

	"outbox/internal/model"
	"outbox/internal/store"
)

var ErrExceeded = errors.New("quota_exceeded")

type Service struct {
	Store *store.Store
}

const Window = time.Hour

func (s *Service) Check(tenant model.Tenant, now time.Time) error {
	okN, err := s.SuccessfulUsage(tenant, now)
	if err != nil {
		return err
	}
	if okN >= tenant.DeliveriesPerHour {
		return ErrExceeded
	}
	return nil
}

func (s *Service) Usage(tenant model.Tenant, now time.Time) (int, error) {
	return s.SuccessfulUsage(tenant, now)
}

// SuccessfulUsage counts delivered outcomes in the rolling window (report coupling).
func (s *Service) SuccessfulUsage(tenant model.Tenant, now time.Time) (int, error) {
	since := now.UTC().Add(-Window)
	return s.Store.CountSuccessfulDeliveriesSince(tenant.ID, since)
}

// Remaining returns how many successful deliveries may still be accepted.
func (s *Service) Remaining(tenant model.Tenant, now time.Time) (int, error) {
	okN, err := s.SuccessfulUsage(tenant, now)
	if err != nil {
		return 0, err
	}
	remain := tenant.DeliveriesPerHour - okN
	if remain < 0 {
		return 0, nil
	}
	return remain, nil
}

// Snapshot bundles usage figures for operator reports.
func (s *Service) Snapshot(tenant model.Tenant, now time.Time) (used, okN, remain int, err error) {
	okN, err = s.SuccessfulUsage(tenant, now)
	if err != nil {
		return
	}
	used = okN
	remain = tenant.DeliveriesPerHour - okN
	if remain < 0 {
		remain = 0
	}
	return
}
