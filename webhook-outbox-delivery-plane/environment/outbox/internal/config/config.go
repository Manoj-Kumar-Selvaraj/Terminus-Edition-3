package config

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type Config struct {
	Root   string
	DBPath string
	Addr   string
	Data   string
	Token  string
	Sync   bool
}

func Load() Config {
	root := getenv("OUTBOX_ROOT", "/app/outbox")
	data := getenv("OUTBOX_DATA", filepath.Join(root, "data"))
	db := getenv("OUTBOX_DB", filepath.Join(data, "outbox.db"))
	addr := getenv("OUTBOX_ADDR", "127.0.0.1:8080")
	token := os.Getenv("OUTBOX_TOKEN")
	sync := getenv("OUTBOX_SYNC", "") == "1"
	return Config{
		Root:   root,
		DBPath: db,
		Addr:   addr,
		Data:   data,
		Token:  token,
		Sync:   sync,
	}
}

func getenv(key, fallback string) string {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return fallback
	}
	return v
}

func (c Config) SchemaPath() string {
	return filepath.Join(c.Root, "db", "schema.sql")
}

func (c Config) UIPath() string {
	return filepath.Join(c.Root, "ui")
}

func ParsePositiveInt(s string, fallback int) int {
	n, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil || n < 1 {
		return fallback
	}
	return n
}
