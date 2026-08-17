package paths

import (
	"os"
	"path/filepath"
)

func Root() string {
	if v := os.Getenv("CATALOG_ROOT"); v != "" {
		return v
	}
	return "/app/catalog"
}

func Data() string       { return filepath.Join(Root(), "data") }
func Out() string        { return filepath.Join(Root(), "out") }
func Config() string     { return filepath.Join(Root(), "config", "catalog.json") }
func EngineDB() string   { return filepath.Join(Data(), "engine.sqlite") }
func WAL() string        { return filepath.Join(Data(), "wal.jsonl") }
func Checkpoint() string { return filepath.Join(Data(), "checkpoint.json") }
func Indexes() string    { return filepath.Join(Data(), "indexes.json") }
func ReplicaDB() string  { return filepath.Join(Data(), "replica.sqlite") }
func ReplicaSlot() string {
	return filepath.Join(Data(), "replica_slot.json")
}
func Warehouse() string  { return filepath.Join(Root(), "warehouse", "inventory.sqlite") }
func SQLReplica() string { return filepath.Join(Root(), "sql", "replica_schema.sql") }
func SQLEngine() string  { return filepath.Join(Root(), "sql", "schema.sql") }
func Health() string     { return filepath.Join(Out(), "health.json") }
func ApplyReport() string {
	return filepath.Join(Out(), "apply-report.json")
}
func CDC() string     { return filepath.Join(Out(), "cdc.jsonl") }
func Rejects() string { return filepath.Join(Out(), "rejects.jsonl") }

func EnsureDirs() error {
	if err := os.MkdirAll(Data(), 0o755); err != nil {
		return err
	}
	return os.MkdirAll(Out(), 0o755)
}
