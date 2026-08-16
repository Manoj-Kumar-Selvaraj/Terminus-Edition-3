package store

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"stackyard/internal/model"

	_ "modernc.org/sqlite"
)

type Store struct {
	DB *sql.DB
}

func Open(dbPath string) (*Store, error) {
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return nil, err
	}
	dsn := dbPath + "?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &Store{DB: db}, nil
}

func (s *Store) Close() error {
	if s == nil || s.DB == nil {
		return nil
	}
	return s.DB.Close()
}

func (s *Store) Migrate(schemaPath string) error {
	body, err := os.ReadFile(schemaPath)
	if err != nil {
		return err
	}
	if _, err := s.DB.Exec(string(body)); err != nil {
		return fmt.Errorf("apply schema: %w", err)
	}
	return nil
}

func (s *Store) EnsureDefaultOrg(ctx context.Context, newID func() string) (*model.Org, error) {
	var id string
	err := s.DB.QueryRowContext(ctx, `SELECT id FROM organizations WHERE slug = ?`, "acme").Scan(&id)
	if err == nil {
		return s.GetOrg(ctx, id)
	}
	if err != sql.ErrNoRows {
		return nil, err
	}
	org := model.Org{
		ID:        newID(),
		Name:      "acme",
		Slug:      "acme",
		CreatedAt: time.Now().UTC(),
	}
	_, err = s.DB.ExecContext(ctx,
		`INSERT INTO organizations(id, name, slug, created_at) VALUES(?,?,?,?)`,
		org.ID, org.Name, org.Slug, org.CreatedAt.Format(time.RFC3339Nano),
	)
	if err != nil {
		return nil, err
	}
	return &org, nil
}

func parseTime(v string) time.Time {
	for _, layout := range []string{time.RFC3339Nano, time.RFC3339} {
		if t, err := time.Parse(layout, v); err == nil {
			return t.UTC()
		}
	}
	return time.Time{}
}

func (s *Store) ListOrgs(ctx context.Context) ([]model.Org, error) {
	rows, err := s.DB.QueryContext(ctx, `SELECT id, name, slug, created_at FROM organizations ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Org
	for rows.Next() {
		var o model.Org
		var created string
		if err := rows.Scan(&o.ID, &o.Name, &o.Slug, &created); err != nil {
			return nil, err
		}
		o.CreatedAt = parseTime(created)
		out = append(out, o)
	}
	return out, rows.Err()
}

func (s *Store) CreateOrg(ctx context.Context, name, slug, id string) (*model.Org, error) {
	org := model.Org{ID: id, Name: name, Slug: slug, CreatedAt: time.Now().UTC()}
	_, err := s.DB.ExecContext(ctx,
		`INSERT INTO organizations(id, name, slug, created_at) VALUES(?,?,?,?)`,
		org.ID, org.Name, org.Slug, org.CreatedAt.Format(time.RFC3339Nano),
	)
	if err != nil {
		return nil, err
	}
	return &org, nil
}

func (s *Store) GetOrg(ctx context.Context, id string) (*model.Org, error) {
	var o model.Org
	var created string
	err := s.DB.QueryRowContext(ctx,
		`SELECT id, name, slug, created_at FROM organizations WHERE id = ?`, id,
	).Scan(&o.ID, &o.Name, &o.Slug, &created)
	if err != nil {
		return nil, err
	}
	o.CreatedAt = parseTime(created)
	return &o, nil
}

func (s *Store) CreateWorkspace(ctx context.Context, orgID, name, workdir, id string) (*model.Workspace, error) {
	ws := model.Workspace{
		ID:               id,
		OrgID:            orgID,
		Name:             name,
		WorkingDirectory: workdir,
		CreatedAt:        time.Now().UTC(),
	}
	_, err := s.DB.ExecContext(ctx,
		`INSERT INTO workspaces(id, org_id, name, working_directory, created_at) VALUES(?,?,?,?,?)`,
		ws.ID, ws.OrgID, ws.Name, ws.WorkingDirectory, ws.CreatedAt.Format(time.RFC3339Nano),
	)
	if err != nil {
		return nil, err
	}
	return s.GetWorkspace(ctx, id)
}

func (s *Store) ListWorkspaces(ctx context.Context, orgID string) ([]model.Workspace, error) {
	// Collect IDs first so we never nest queries against MaxOpenConns(1).
	rows, err := s.DB.QueryContext(ctx, `SELECT id FROM workspaces WHERE org_id = ? ORDER BY name`, orgID)
	if err != nil {
		return nil, err
	}
	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			_ = rows.Close()
			return nil, err
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	out := make([]model.Workspace, 0, len(ids))
	for _, id := range ids {
		ws, err := s.GetWorkspace(ctx, id)
		if err != nil {
			return nil, err
		}
		out = append(out, *ws)
	}
	return out, nil
}

func (s *Store) GetWorkspace(ctx context.Context, id string) (*model.Workspace, error) {
	var ws model.Workspace
	var created string
	err := s.DB.QueryRowContext(ctx,
		`SELECT id, org_id, name, working_directory, created_at FROM workspaces WHERE id = ?`, id,
	).Scan(&ws.ID, &ws.OrgID, &ws.Name, &ws.WorkingDirectory, &created)
	if err != nil {
		return nil, err
	}
	ws.CreatedAt = parseTime(created)
	var lockID sql.NullString
	err = s.DB.QueryRowContext(ctx, `SELECT id FROM locks WHERE workspace_id = ?`, id).Scan(&lockID)
	if err == nil && lockID.Valid {
		ws.Locked = true
		ws.LockID = &lockID.String
	} else if err != nil && err != sql.ErrNoRows {
		return nil, err
	}
	return &ws, nil
}

func (s *Store) CountNonTerminalRuns(ctx context.Context, workspaceID string) (int, error) {
	var n int
	err := s.DB.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM runs
		WHERE workspace_id = ? AND status IN ('queued','running','planned')
	`, workspaceID).Scan(&n)
	return n, err
}

func (s *Store) DeleteWorkspace(ctx context.Context, id string) error {
	res, err := s.DB.ExecContext(ctx, `DELETE FROM workspaces WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (s *Store) CreateVariable(ctx context.Context, v model.Variable) (*model.Variable, error) {
	sens := 0
	if v.Sensitive {
		sens = 1
	}
	_, err := s.DB.ExecContext(ctx, `
		INSERT INTO variables(id, workspace_id, key, value, sensitive, category, created_at)
		VALUES(?,?,?,?,?,?,?)
	`, v.ID, v.WorkspaceID, v.Key, v.RawValue, sens, v.Category, v.CreatedAt.Format(time.RFC3339Nano))
	if err != nil {
		return nil, err
	}
	return s.GetVariable(ctx, v.ID)
}

func (s *Store) GetVariable(ctx context.Context, id string) (*model.Variable, error) {
	var v model.Variable
	var created string
	var sens int
	var raw string
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, workspace_id, key, value, sensitive, category, created_at
		FROM variables WHERE id = ?
	`, id).Scan(&v.ID, &v.WorkspaceID, &v.Key, &raw, &sens, &v.Category, &created)
	if err != nil {
		return nil, err
	}
	v.Sensitive = sens == 1
	v.RawValue = raw
	v.CreatedAt = parseTime(created)
	return &v, nil
}

func (s *Store) ListVariables(ctx context.Context, workspaceID string) ([]model.Variable, error) {
	rows, err := s.DB.QueryContext(ctx, `
		SELECT id FROM variables WHERE workspace_id = ? ORDER BY key
	`, workspaceID)
	if err != nil {
		return nil, err
	}
	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			_ = rows.Close()
			return nil, err
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	out := make([]model.Variable, 0, len(ids))
	for _, id := range ids {
		v, err := s.GetVariable(ctx, id)
		if err != nil {
			return nil, err
		}
		out = append(out, *v)
	}
	return out, nil
}

func (s *Store) DeleteVariable(ctx context.Context, id string) error {
	res, err := s.DB.ExecContext(ctx, `DELETE FROM variables WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (s *Store) CreateRun(ctx context.Context, r model.Run) (*model.Run, error) {
	_, err := s.DB.ExecContext(ctx, `
		INSERT INTO runs(id, workspace_id, command, status, message, plan_output, apply_output, error, created_at, updated_at)
		VALUES(?,?,?,?,?,?,?,?,?,?)
	`, r.ID, r.WorkspaceID, r.Command, r.Status, r.Message, r.PlanOutput, r.ApplyOutput, r.Error,
		r.CreatedAt.Format(time.RFC3339Nano), r.UpdatedAt.Format(time.RFC3339Nano))
	if err != nil {
		return nil, err
	}
	return s.GetRun(ctx, r.ID)
}

func (s *Store) GetRun(ctx context.Context, id string) (*model.Run, error) {
	var r model.Run
	var created, updated string
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, workspace_id, command, status, message, plan_output, apply_output, error, created_at, updated_at
		FROM runs WHERE id = ?
	`, id).Scan(&r.ID, &r.WorkspaceID, &r.Command, &r.Status, &r.Message, &r.PlanOutput, &r.ApplyOutput, &r.Error, &created, &updated)
	if err != nil {
		return nil, err
	}
	r.CreatedAt = parseTime(created)
	r.UpdatedAt = parseTime(updated)
	return &r, nil
}

func (s *Store) ListRuns(ctx context.Context, workspaceID string) ([]model.Run, error) {
	rows, err := s.DB.QueryContext(ctx, `
		SELECT id FROM runs WHERE workspace_id = ? ORDER BY created_at DESC
	`, workspaceID)
	if err != nil {
		return nil, err
	}
	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			_ = rows.Close()
			return nil, err
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	out := make([]model.Run, 0, len(ids))
	for _, id := range ids {
		r, err := s.GetRun(ctx, id)
		if err != nil {
			return nil, err
		}
		out = append(out, *r)
	}
	return out, nil
}

func (s *Store) UpdateRun(ctx context.Context, r model.Run) error {
	r.UpdatedAt = time.Now().UTC()
	_, err := s.DB.ExecContext(ctx, `
		UPDATE runs SET status=?, plan_output=?, apply_output=?, error=?, updated_at=? WHERE id=?
	`, r.Status, r.PlanOutput, r.ApplyOutput, r.Error, r.UpdatedAt.Format(time.RFC3339Nano), r.ID)
	return err
}

func (s *Store) CreateLock(ctx context.Context, l model.Lock) (*model.Lock, error) {
	_, err := s.DB.ExecContext(ctx, `
		INSERT INTO locks(id, workspace_id, holder, reason, created_at) VALUES(?,?,?,?,?)
	`, l.ID, l.WorkspaceID, l.Holder, l.Reason, l.CreatedAt.Format(time.RFC3339Nano))
	if err != nil {
		if strings.Contains(strings.ToLower(err.Error()), "unique") {
			return nil, err
		}
		return nil, err
	}
	return s.GetLock(ctx, l.WorkspaceID)
}

func (s *Store) GetLock(ctx context.Context, workspaceID string) (*model.Lock, error) {
	var l model.Lock
	var created string
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, workspace_id, holder, reason, created_at FROM locks WHERE workspace_id = ?
	`, workspaceID).Scan(&l.ID, &l.WorkspaceID, &l.Holder, &l.Reason, &created)
	if err != nil {
		return nil, err
	}
	l.CreatedAt = parseTime(created)
	return &l, nil
}

func (s *Store) DeleteLock(ctx context.Context, workspaceID string) error {
	_, err := s.DB.ExecContext(ctx, `DELETE FROM locks WHERE workspace_id = ?`, workspaceID)
	return err
}

func (s *Store) InsertAudit(ctx context.Context, ev model.AuditEvent) error {
	_, err := s.DB.ExecContext(ctx, `
		INSERT INTO audit_events(id, workspace_id, action, detail, actor, created_at)
		VALUES(?,?,?,?,?,?)
	`, ev.ID, ev.WorkspaceID, ev.Action, ev.Detail, ev.Actor, ev.CreatedAt.Format(time.RFC3339Nano))
	return err
}

func (s *Store) ListAudit(ctx context.Context, workspaceID string) ([]model.AuditEvent, error) {
	rows, err := s.DB.QueryContext(ctx, `
		SELECT id, workspace_id, action, detail, actor, created_at
		FROM audit_events WHERE workspace_id = ? ORDER BY created_at DESC
	`, workspaceID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.AuditEvent
	for rows.Next() {
		var ev model.AuditEvent
		var created string
		if err := rows.Scan(&ev.ID, &ev.WorkspaceID, &ev.Action, &ev.Detail, &ev.Actor, &created); err != nil {
			return nil, err
		}
		ev.CreatedAt = parseTime(created)
		out = append(out, ev)
	}
	return out, rows.Err()
}
