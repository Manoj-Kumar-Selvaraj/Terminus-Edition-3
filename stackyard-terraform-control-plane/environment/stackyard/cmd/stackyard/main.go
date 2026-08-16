package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"stackyard/internal/api"
	"stackyard/internal/config"
	"stackyard/internal/store"
)

func main() {
	productRoot := detectRoot()
	cfg := config.Load(productRoot)
	if err := os.MkdirAll(cfg.DataDir, 0o755); err != nil {
		log.Fatalf("data dir: %v", err)
	}
	st, err := store.Open(cfg.DBPath)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer st.Close()
	if err := st.Migrate(cfg.SchemaPath); err != nil {
		log.Fatalf("migrate: %v", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if _, err := st.EnsureDefaultOrg(ctx, func() string {
		return fmt.Sprintf("org_%d", time.Now().UnixNano())
	}); err != nil {
		log.Fatalf("seed org: %v", err)
	}

	srv := api.New(cfg, st)
	log.Printf("stackyard listening on http://%s (db=%s)", cfg.Addr, cfg.DBPath)
	if err := http.ListenAndServe(cfg.Addr, srv.Handler()); err != nil {
		log.Fatal(err)
	}
}

func detectRoot() string {
	if v := os.Getenv("STACKYARD_ROOT"); v != "" {
		return v
	}
	candidates := []string{"/app/stackyard", "."}
	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(c, "db", "schema.sql")); err == nil {
			abs, err := filepath.Abs(c)
			if err == nil {
				return abs
			}
			return c
		}
	}
	wd, _ := os.Getwd()
	return wd
}
