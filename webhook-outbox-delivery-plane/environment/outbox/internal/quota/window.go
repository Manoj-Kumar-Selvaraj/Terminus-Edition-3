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
	since := now.UTC().Add(-Window)
	n, err := s.Store.CountAllAttemptsSince(tenant.ID, since)
	if err != nil {
		return err
	}
	if n >= tenant.DeliveriesPerHour {
		return ErrExceeded
	}
	return nil
}

func (s *Service) Usage(tenant model.Tenant, now time.Time) (int, error) {
	since := now.UTC().Add(-Window)
	return s.Store.CountAllAttemptsSince(tenant.ID, since)
}
