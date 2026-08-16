package store

import (
	"time"

	"outbox/internal/model"
)

func (s *Store) InsertAttempt(eventID, tenantID string, attemptNo int, outcome string, httpStatus int, errMsg string) (model.Attempt, error) {
	now := s.Now()
	a := model.Attempt{
		ID:         model.NewAttemptID(),
		EventID:    eventID,
		AttemptNo:  attemptNo,
		Outcome:    outcome,
		HTTPStatus: httpStatus,
		Error:      errMsg,
		CreatedAt:  now,
	}
	_, err := s.db.Exec(
		`INSERT INTO delivery_attempts(id,event_id,tenant_id,attempt_no,outcome,http_status,error,created_at)
		 VALUES(?,?,?,?,?,?,?,?)`,
		a.ID, a.EventID, tenantID, a.AttemptNo, a.Outcome, a.HTTPStatus, a.Error, model.FormatTime(a.CreatedAt),
	)
	if err != nil {
		return model.Attempt{}, err
	}
	return a, nil
}

func (s *Store) ListAttempts(eventID string) ([]model.Attempt, error) {
	rows, err := s.db.Query(
		`SELECT id,event_id,attempt_no,outcome,http_status,error,created_at
		 FROM delivery_attempts WHERE event_id=? ORDER BY attempt_no ASC`, eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Attempt
	for rows.Next() {
		var a model.Attempt
		var created string
		if err := rows.Scan(&a.ID, &a.EventID, &a.AttemptNo, &a.Outcome, &a.HTTPStatus, &a.Error, &created); err != nil {
			return nil, err
		}
		ts, err := model.ParseTime(created)
		if err != nil {
			return nil, err
		}
		a.CreatedAt = ts
		out = append(out, a)
	}
	return out, rows.Err()
}

func (s *Store) CountSuccessfulDeliveriesSince(tenantID string, since time.Time) (int, error) {
	var n int
	err := s.db.QueryRow(
		`SELECT COUNT(*) FROM delivery_attempts
		 WHERE tenant_id=? AND outcome=? AND created_at >= ?`,
		tenantID, model.OutcomeDelivered, model.FormatTime(since),
	).Scan(&n)
	return n, err
}

// CountAllAttemptsSince is intentionally available for diagnostics; quota must not use it.
func (s *Store) CountAllAttemptsSince(tenantID string, since time.Time) (int, error) {
	var n int
	err := s.db.QueryRow(
		`SELECT COUNT(*) FROM delivery_attempts WHERE tenant_id=? AND created_at >= ?`,
		tenantID, model.FormatTime(since),
	).Scan(&n)
	return n, err
}

func (s *Store) CountAttempts() (int, error) {
	var n int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM delivery_attempts`).Scan(&n)
	return n, err
}
