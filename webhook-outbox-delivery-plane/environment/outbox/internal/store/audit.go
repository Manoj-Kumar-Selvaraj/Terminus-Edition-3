package store

import (
	"encoding/json"

	"outbox/internal/model"
)

func (s *Store) InsertAudit(action, entityType, entityID, actor string, detail map[string]any) (model.AuditEvent, error) {
	if detail == nil {
		detail = map[string]any{}
	}
	raw, err := json.Marshal(detail)
	if err != nil {
		return model.AuditEvent{}, err
	}
	now := s.Now()
	a := model.AuditEvent{
		ID:         model.NewAuditID(),
		Action:     action,
		EntityType: entityType,
		EntityID:   entityID,
		Actor:      actor,
		Detail:     detail,
		CreatedAt:  now,
	}
	_, err = s.db.Exec(
		`INSERT INTO audit_events(id,action,entity_type,entity_id,actor,detail,created_at) VALUES(?,?,?,?,?,?,?)`,
		a.ID, a.Action, a.EntityType, a.EntityID, a.Actor, string(raw), model.FormatTime(a.CreatedAt),
	)
	if err != nil {
		return model.AuditEvent{}, err
	}
	return a, nil
}

func (s *Store) ListAudit(limit int) ([]model.AuditEvent, error) {
	if limit < 1 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}
	rows, err := s.db.Query(
		`SELECT id,action,entity_type,entity_id,actor,detail,created_at FROM audit_events ORDER BY created_at DESC LIMIT ?`, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.AuditEvent
	for rows.Next() {
		var a model.AuditEvent
		var detail, created string
		if err := rows.Scan(&a.ID, &a.Action, &a.EntityType, &a.EntityID, &a.Actor, &detail, &created); err != nil {
			return nil, err
		}
		_ = json.Unmarshal([]byte(detail), &a.Detail)
		if a.Detail == nil {
			a.Detail = map[string]any{}
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

func (s *Store) CountAuditByAction(action string) (int, error) {
	var n int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM audit_events WHERE action=?`, action).Scan(&n)
	return n, err
}
