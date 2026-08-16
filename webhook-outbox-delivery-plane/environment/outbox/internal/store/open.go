package store

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"

	"outbox/internal/clock"
)

type Store struct {
	db    *sql.DB
	clock clock.Clock
}

func Open(dbPath, schemaSQL string, clk clock.Clock) (*Store, error) {
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return nil, err
	}
	dsn := fmt.Sprintf("file:%s?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)", filepath.ToSlash(dbPath))
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(0)
	if clk == nil {
		clk = clock.System{}
	}
	s := &Store{db: db, clock: clk}
	if err := s.applySchema(schemaSQL); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	return s.db.Close()
}

func (s *Store) DB() *sql.DB { return s.db }

func (s *Store) Now() time.Time { return s.clock.Now().UTC() }

func (s *Store) applySchema(schemaSQL string) error {
	raw, err := os.ReadFile(schemaSQL)
	if err != nil {
		return err
	}
	_, err = s.db.Exec(string(raw))
	return err
}

func (s *Store) WithTx(fn func(tx *sql.Tx) error) error {
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	if err := fn(tx); err != nil {
		return err
	}
	return tx.Commit()
}

func nullStr(p *string) sql.NullString {
	if p == nil || *p == "" {
		return sql.NullString{}
	}
	return sql.NullString{String: *p, Valid: true}
}

func nullTime(p *time.Time) sql.NullString {
	if p == nil || p.IsZero() {
		return sql.NullString{}
	}
	return sql.NullString{String: p.UTC().Format(time.RFC3339Nano), Valid: true}
}

func scanNullString(ns sql.NullString) *string {
	if !ns.Valid {
		return nil
	}
	v := ns.String
	return &v
}

func scanNullTime(ns sql.NullString) (*time.Time, error) {
	if !ns.Valid || ns.String == "" {
		return nil, nil
	}
	t, err := time.Parse(time.RFC3339Nano, ns.String)
	if err != nil {
		t, err = time.Parse(time.RFC3339, ns.String)
		if err != nil {
			return nil, err
		}
	}
	u := t.UTC()
	return &u, nil
}

func boolToInt(v bool) int {
	if v {
		return 1
	}
	return 0
}

func intToBool(v int) bool { return v != 0 }

func trimSQL(s string) string { return strings.TrimSpace(s) }
