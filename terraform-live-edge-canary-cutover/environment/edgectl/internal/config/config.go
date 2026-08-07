// Package config loads the optional on-disk edgectl control-plane document
// used for digests and simulator tuning.
package config

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
)

// Config is the JSON document rendered beside the control-plane binary.
type Config struct {
	// Version is a free-form release label surfaced in health checks.
	Version string `json:"version"`
	// TickMillis is how often the traffic simulator emits a synthetic request.
	TickMillis int `json:"tick_millis"`
	// WindowSize is the sliding window used for recent error_rate_pct.
	WindowSize int `json:"window_size"`
	// UnhealthyErrorRate is the fraction of requests that fail when a pool
	// has no healthy origins (0.0–1.0). Defaults to 1.0 (always fail).
	UnhealthyErrorRate float64 `json:"unhealthy_error_rate"`
	// BaseErrorRate is background noise applied even to healthy origins.
	BaseErrorRate float64 `json:"base_error_rate"`

	Digest string `json:"-"`
}

// Defaults returns a usable configuration when the file is missing or sparse.
func Defaults() *Config {
	return &Config{
		Version:            "edgectl-1",
		TickMillis:         50,
		WindowSize:         200,
		UnhealthyErrorRate: 1.0,
		BaseErrorRate:      0.0,
	}
}

// Load reads, digests, and validates the configuration document. Missing
// fields are filled from Defaults. An empty or absent file yields defaults
// with a stable digest of the normalized defaults.
func Load(path string) (*Config, error) {
	cfg := Defaults()

	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			cfg.Digest = digestConfig(cfg)
			return cfg, nil
		}
		return nil, err
	}
	if len(bytes.TrimSpace(raw)) == 0 {
		cfg.Digest = digestConfig(cfg)
		return cfg, nil
	}

	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(cfg); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	cfg.Digest = digestConfig(cfg)
	return cfg, nil
}

func digestConfig(cfg *Config) string {
	// Digest only the persisted fields so flag overrides do not churn it.
	type wire struct {
		Version            string  `json:"version"`
		TickMillis         int     `json:"tick_millis"`
		WindowSize         int     `json:"window_size"`
		UnhealthyErrorRate float64 `json:"unhealthy_error_rate"`
		BaseErrorRate      float64 `json:"base_error_rate"`
	}
	blob, _ := json.Marshal(wire{
		Version:            cfg.Version,
		TickMillis:         cfg.TickMillis,
		WindowSize:         cfg.WindowSize,
		UnhealthyErrorRate: cfg.UnhealthyErrorRate,
		BaseErrorRate:      cfg.BaseErrorRate,
	})
	sum := sha256.Sum256(blob)
	return hex.EncodeToString(sum[:])
}

func (c *Config) validate() error {
	if c.Version == "" {
		c.Version = "edgectl-1"
	}
	if c.TickMillis <= 0 {
		c.TickMillis = 50
	}
	if c.WindowSize <= 0 {
		c.WindowSize = 200
	}
	if c.UnhealthyErrorRate < 0 || c.UnhealthyErrorRate > 1 {
		return fmt.Errorf("unhealthy_error_rate must be between 0 and 1")
	}
	if c.BaseErrorRate < 0 || c.BaseErrorRate > 1 {
		return fmt.Errorf("base_error_rate must be between 0 and 1")
	}
	return nil
}
