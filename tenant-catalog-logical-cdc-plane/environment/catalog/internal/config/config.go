package config

import (
	"encoding/json"
	"os"

	"catalog/internal/paths"
)

type Catalog struct {
	Isolation    string `json:"isolation"`
	ReplicaEpoch int64  `json:"replica_epoch"`
	CDCSource    string `json:"cdc_source"`
}

func Load() (Catalog, error) {
	cfg := Catalog{Isolation: "snapshot", ReplicaEpoch: 1, CDCSource: "wal"}
	b, err := os.ReadFile(paths.Config())
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return cfg, err
	}
	if err := json.Unmarshal(b, &cfg); err != nil {
		return cfg, err
	}
	if cfg.Isolation == "" {
		cfg.Isolation = "snapshot"
	}
	if cfg.CDCSource == "" {
		cfg.CDCSource = "wal"
	}
	if cfg.ReplicaEpoch <= 0 {
		cfg.ReplicaEpoch = 1
	}
	return cfg, nil
}
