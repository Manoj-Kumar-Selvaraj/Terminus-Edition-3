package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"outbox/internal/model"
)

type EventRow struct {
	Event          model.Event
	PayloadRaw     string
}

func (s *Store) InsertEvent(tenantID, endpointID string, payload []byte, idem *string, status string) (model.Event, error) {
	now := s.Now()
	ev := model.Event{
		ID:             model.NewEventID(),
		TenantID:       tenantID,
		EndpointID:     endpointID,
		IdempotencyKey: idem,
		Status:         status,
		AttemptCount:   0,
		NextAttemptAt:  now,
		CreatedAt:      now,
		UpdatedAt:      now,
	}
	var payloadObj any
	if err := json.Unmarshal(payload, &payloadObj); err != nil {
		return model.Event{}, err
	}
	ev.Payload = payloadObj
	_, err := s.db.Exec(
		`INSERT INTO events(id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at)
		 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`,
		ev.ID, ev.TenantID, ev.EndpointID, string(payload), nullStr(idem), ev.Status, ev.AttemptCount,
		nil, nil, model.FormatTime(ev.NextAttemptAt), model.FormatTime(ev.CreatedAt), model.FormatTime(ev.UpdatedAt),
	)
	if err != nil {
		if isUnique(err) && idem != nil && *idem != "" {
			existing, gerr := s.GetEventByIdempotency(endpointID, *idem)
			if gerr == nil {
				return existing, ErrConflict
			}
		}
		return model.Event{}, err
	}
	return ev, nil
}

func (s *Store) GetEvent(id string) (model.Event, error) {
	row := s.db.QueryRow(
		`SELECT id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at
		 FROM events WHERE id=?`, id,
	)
	return scanEvent(row)
}

func (s *Store) GetEventByIdempotency(endpointID, key string) (model.Event, error) {
	row := s.db.QueryRow(
		`SELECT id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at
		 FROM events WHERE endpoint_id=? AND idempotency_key=?`, endpointID, key,
	)
	return scanEvent(row)
}

func (s *Store) ListEvents(tenantID, status string, limit int) ([]model.Event, error) {
	if limit < 1 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}
	var rows *sql.Rows
	var err error
	if status == "" {
		rows, err = s.db.Query(
			`SELECT id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at
			 FROM events WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?`, tenantID, limit,
		)
	} else {
		rows, err = s.db.Query(
			`SELECT id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at
			 FROM events WHERE tenant_id=? AND status=? ORDER BY created_at DESC LIMIT ?`, tenantID, status, limit,
		)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Event
	for rows.Next() {
		ev, err := scanEventRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, ev)
	}
	return out, rows.Err()
}

func (s *Store) UpdateEventLease(id, owner string, until time.Time, status string) error {
	now := s.Now()
	res, err := s.db.Exec(
		`UPDATE events SET lease_owner=?, lease_until=?, status=?, updated_at=? WHERE id=?`,
		owner, model.FormatTime(until), status, model.FormatTime(now), id,
	)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func (s *Store) ClearEventLease(id, status string, next time.Time, attemptCount int) error {
	now := s.Now()
	res, err := s.db.Exec(
		`UPDATE events SET lease_owner=NULL, lease_until=NULL, status=?, next_attempt_at=?, attempt_count=?, updated_at=? WHERE id=?`,
		status, model.FormatTime(next), attemptCount, model.FormatTime(now), id,
	)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func (s *Store) MarkDelivered(id string) error {
	now := s.Now()
	res, err := s.db.Exec(
		`UPDATE events SET status=?, lease_owner=NULL, lease_until=NULL, updated_at=? WHERE id=?`,
		model.StatusDelivered, model.FormatTime(now), id,
	)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func (s *Store) CountEventsByStatus() (map[string]int, error) {
	rows, err := s.db.Query(`SELECT status, COUNT(*) FROM events GROUP BY status`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]int{}
	for rows.Next() {
		var st string
		var n int
		if err := rows.Scan(&st, &n); err != nil {
			return nil, err
		}
		out[st] = n
	}
	return out, rows.Err()
}

func (s *Store) CountEvents() (int, error) {
	var n int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM events`).Scan(&n)
	return n, err
}

func scanEvent(row *sql.Row) (model.Event, error) {
	var ev model.Event
	var payload string
	var idem, owner, until sql.NullString
	var next, created, updated string
	err := row.Scan(&ev.ID, &ev.TenantID, &ev.EndpointID, &payload, &idem, &ev.Status, &ev.AttemptCount, &owner, &until, &next, &created, &updated)
	if errors.Is(err, sql.ErrNoRows) {
		return model.Event{}, ErrNotFound
	}
	if err != nil {
		return model.Event{}, err
	}
	return finishEvent(ev, payload, idem, owner, until, next, created, updated)
}

func scanEventRows(rows *sql.Rows) (model.Event, error) {
	var ev model.Event
	var payload string
	var idem, owner, until sql.NullString
	var next, created, updated string
	if err := rows.Scan(&ev.ID, &ev.TenantID, &ev.EndpointID, &payload, &idem, &ev.Status, &ev.AttemptCount, &owner, &until, &next, &created, &updated); err != nil {
		return model.Event{}, err
	}
	return finishEvent(ev, payload, idem, owner, until, next, created, updated)
}

func finishEvent(ev model.Event, payload string, idem, owner, until sql.NullString, next, created, updated string) (model.Event, error) {
	var obj any
	if err := json.Unmarshal([]byte(payload), &obj); err != nil {
		return model.Event{}, fmt.Errorf("payload: %w", err)
	}
	ev.Payload = obj
	ev.IdempotencyKey = scanNullString(idem)
	ev.LeaseOwner = scanNullString(owner)
	lt, err := scanNullTime(until)
	if err != nil {
		return model.Event{}, err
	}
	ev.LeaseUntil = lt
	ev.NextAttemptAt, err = model.ParseTime(next)
	if err != nil {
		return model.Event{}, err
	}
	ev.CreatedAt, err = model.ParseTime(created)
	if err != nil {
		return model.Event{}, err
	}
	ev.UpdatedAt, err = model.ParseTime(updated)
	if err != nil {
		return model.Event{}, err
	}
	return ev, nil
}

func (s *Store) PayloadBytes(ev model.Event) ([]byte, error) {
	return json.Marshal(ev.Payload)
}
