package store

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"outbox/internal/model"
)

var ErrNotFound = errors.New("not_found")
var ErrConflict = errors.New("conflict")

func (s *Store) CreateTenant(name, slug string, quota int) (model.Tenant, error) {
	now := s.Now()
	t := model.Tenant{
		ID:                model.NewTenantID(),
		Name:              name,
		Slug:              slug,
		DeliveriesPerHour: quota,
		CreatedAt:         now,
	}
	_, err := s.db.Exec(
		`INSERT INTO tenants(id,name,slug,deliveries_per_hour,created_at) VALUES(?,?,?,?,?)`,
		t.ID, t.Name, t.Slug, t.DeliveriesPerHour, model.FormatTime(t.CreatedAt),
	)
	if err != nil {
		if isUnique(err) {
			return model.Tenant{}, fmt.Errorf("%w: slug", ErrConflict)
		}
		return model.Tenant{}, err
	}
	return t, nil
}

func (s *Store) GetTenant(id string) (model.Tenant, error) {
	row := s.db.QueryRow(`SELECT id,name,slug,deliveries_per_hour,created_at FROM tenants WHERE id=?`, id)
	return scanTenant(row)
}

func (s *Store) GetTenantBySlug(slug string) (model.Tenant, error) {
	row := s.db.QueryRow(`SELECT id,name,slug,deliveries_per_hour,created_at FROM tenants WHERE slug=?`, slug)
	return scanTenant(row)
}

func (s *Store) ListTenants() ([]model.Tenant, error) {
	rows, err := s.db.Query(`SELECT id,name,slug,deliveries_per_hour,created_at FROM tenants ORDER BY created_at ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Tenant
	for rows.Next() {
		t, err := scanTenantRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

func scanTenant(row *sql.Row) (model.Tenant, error) {
	var t model.Tenant
	var created string
	err := row.Scan(&t.ID, &t.Name, &t.Slug, &t.DeliveriesPerHour, &created)
	if errors.Is(err, sql.ErrNoRows) {
		return model.Tenant{}, ErrNotFound
	}
	if err != nil {
		return model.Tenant{}, err
	}
	ts, err := model.ParseTime(created)
	if err != nil {
		return model.Tenant{}, err
	}
	t.CreatedAt = ts
	return t, nil
}

func scanTenantRows(rows *sql.Rows) (model.Tenant, error) {
	var t model.Tenant
	var created string
	if err := rows.Scan(&t.ID, &t.Name, &t.Slug, &t.DeliveriesPerHour, &created); err != nil {
		return model.Tenant{}, err
	}
	ts, err := model.ParseTime(created)
	if err != nil {
		return model.Tenant{}, err
	}
	t.CreatedAt = ts
	return t, nil
}

func isUnique(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return containsFold(msg, "unique") || containsFold(msg, "constraint")
}

func containsFold(s, sub string) bool {
	return len(s) >= len(sub) && (stringIndexFold(s, sub) >= 0)
}

func stringIndexFold(s, sub string) int {
	ls, lsub := len(s), len(sub)
	for i := 0; i+lsub <= ls; i++ {
		ok := true
		for j := 0; j < lsub; j++ {
			a, b := s[i+j], sub[j]
			if a >= 'A' && a <= 'Z' {
				a += 32
			}
			if b >= 'A' && b <= 'Z' {
				b += 32
			}
			if a != b {
				ok = false
				break
			}
		}
		if ok {
			return i
		}
	}
	return -1
}

func (s *Store) CountTenants() (int, error) {
	var n int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM tenants`).Scan(&n)
	return n, err
}

func (s *Store) EnsureTenant(name, slug string, quota int) (model.Tenant, error) {
	t, err := s.GetTenantBySlug(slug)
	if err == nil {
		return t, nil
	}
	if !errors.Is(err, ErrNotFound) {
		return model.Tenant{}, err
	}
	return s.CreateTenant(name, slug, quota)
}

func unusedTime() time.Time { return time.Time{} }
