package store

import (
	"database/sql"
	"errors"

	"outbox/internal/model"
)

func (s *Store) CreateEndpoint(tenantID, name, url, secret string, enabled bool, maxAttempts int) (model.Endpoint, error) {
	now := s.Now()
	ep := model.Endpoint{
		ID:          model.NewEndpointID(),
		TenantID:    tenantID,
		Name:        name,
		URL:         url,
		HMACSecret:  secret,
		Enabled:     enabled,
		Paused:      false,
		MaxAttempts: maxAttempts,
		CreatedAt:   now,
	}
	_, err := s.db.Exec(
		`INSERT INTO endpoints(id,tenant_id,name,url,hmac_secret,enabled,paused,max_attempts,created_at)
		 VALUES(?,?,?,?,?,?,?,?,?)`,
		ep.ID, ep.TenantID, ep.Name, ep.URL, ep.HMACSecret, boolToInt(ep.Enabled), boolToInt(ep.Paused), ep.MaxAttempts, model.FormatTime(ep.CreatedAt),
	)
	if err != nil {
		return model.Endpoint{}, err
	}
	return ep, nil
}

func (s *Store) GetEndpoint(id string) (model.Endpoint, error) {
	row := s.db.QueryRow(
		`SELECT id,tenant_id,name,url,hmac_secret,enabled,paused,max_attempts,created_at FROM endpoints WHERE id=?`, id,
	)
	return scanEndpoint(row)
}

func (s *Store) ListEndpoints(tenantID string) ([]model.Endpoint, error) {
	rows, err := s.db.Query(
		`SELECT id,tenant_id,name,url,hmac_secret,enabled,paused,max_attempts,created_at
		 FROM endpoints WHERE tenant_id=? ORDER BY created_at ASC`, tenantID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Endpoint
	for rows.Next() {
		ep, err := scanEndpointRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, ep)
	}
	return out, rows.Err()
}

func (s *Store) SetEndpointPaused(id string, paused bool) (model.Endpoint, error) {
	res, err := s.db.Exec(`UPDATE endpoints SET paused=? WHERE id=?`, boolToInt(paused), id)
	if err != nil {
		return model.Endpoint{}, err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return model.Endpoint{}, ErrNotFound
	}
	return s.GetEndpoint(id)
}

func (s *Store) PatchEndpoint(id string, name, url, secret *string, enabled *bool, maxAttempts *int) (model.Endpoint, error) {
	ep, err := s.GetEndpoint(id)
	if err != nil {
		return model.Endpoint{}, err
	}
	if name != nil {
		ep.Name = *name
	}
	if url != nil {
		ep.URL = *url
	}
	if secret != nil {
		ep.HMACSecret = *secret
	}
	if enabled != nil {
		ep.Enabled = *enabled
	}
	if maxAttempts != nil {
		ep.MaxAttempts = *maxAttempts
	}
	_, err = s.db.Exec(
		`UPDATE endpoints SET name=?, url=?, hmac_secret=?, enabled=?, max_attempts=? WHERE id=?`,
		ep.Name, ep.URL, ep.HMACSecret, boolToInt(ep.Enabled), ep.MaxAttempts, id,
	)
	if err != nil {
		return model.Endpoint{}, err
	}
	return s.GetEndpoint(id)
}

func (s *Store) CountEndpoints() (int, error) {
	var n int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM endpoints`).Scan(&n)
	return n, err
}

func scanEndpoint(row *sql.Row) (model.Endpoint, error) {
	var ep model.Endpoint
	var enabled, paused int
	var created string
	err := row.Scan(&ep.ID, &ep.TenantID, &ep.Name, &ep.URL, &ep.HMACSecret, &enabled, &paused, &ep.MaxAttempts, &created)
	if errors.Is(err, sql.ErrNoRows) {
		return model.Endpoint{}, ErrNotFound
	}
	if err != nil {
		return model.Endpoint{}, err
	}
	ep.Enabled = intToBool(enabled)
	ep.Paused = intToBool(paused)
	ts, err := model.ParseTime(created)
	if err != nil {
		return model.Endpoint{}, err
	}
	ep.CreatedAt = ts
	return ep, nil
}

func scanEndpointRows(rows *sql.Rows) (model.Endpoint, error) {
	var ep model.Endpoint
	var enabled, paused int
	var created string
	if err := rows.Scan(&ep.ID, &ep.TenantID, &ep.Name, &ep.URL, &ep.HMACSecret, &enabled, &paused, &ep.MaxAttempts, &created); err != nil {
		return model.Endpoint{}, err
	}
	ep.Enabled = intToBool(enabled)
	ep.Paused = intToBool(paused)
	ts, err := model.ParseTime(created)
	if err != nil {
		return model.Endpoint{}, err
	}
	ep.CreatedAt = ts
	return ep, nil
}
