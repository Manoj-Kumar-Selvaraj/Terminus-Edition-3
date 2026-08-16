package config

import (
	"os"
	"path/filepath"
)

type Config struct {
	DBPath       string
	Addr         string
	DataDir      string
	TerraformBin string
	Token        string
	SchemaPath   string
	UIDir        string
	SyncRuns     bool
}

func Load(productRoot string) Config {
	db := envOr("STACKYARD_DB", filepath.Join(productRoot, "data", "stackyard.db"))
	data := envOr("STACKYARD_DATA", filepath.Join(productRoot, "data", "workspaces"))
	bin := envOr("TERRAFORM_BIN", filepath.Join(productRoot, "bin", "terraform-shim"))
	return Config{
		DBPath:       db,
		Addr:         envOr("STACKYARD_ADDR", "127.0.0.1:8080"),
		DataDir:      data,
		TerraformBin: bin,
		Token:        os.Getenv("STACKYARD_TOKEN"),
		SchemaPath:   filepath.Join(productRoot, "db", "schema.sql"),
		UIDir:        filepath.Join(productRoot, "ui"),
		SyncRuns:     os.Getenv("STACKYARD_SYNC") == "1",
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
