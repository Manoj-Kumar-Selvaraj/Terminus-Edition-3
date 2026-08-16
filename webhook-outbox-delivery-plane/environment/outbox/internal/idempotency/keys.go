package idempotency

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"unicode"
)

// Normalize trims and lowercases operator-provided idempotency keys.
func Normalize(key string) string {
	key = strings.TrimSpace(key)
	if key == "" {
		return ""
	}
	var b strings.Builder
	for _, r := range key {
		if unicode.IsSpace(r) {
			continue
		}
		b.WriteRune(unicode.ToLower(r))
	}
	return b.String()
}

// Fingerprint hashes endpoint + key for diagnostic logs (not stored as PK).
func Fingerprint(endpointID, key string) string {
	sum := sha256.Sum256([]byte(endpointID + "\x00" + Normalize(key)))
	return hex.EncodeToString(sum[:16])
}

func Valid(key string) bool {
	n := Normalize(key)
	if n == "" {
		return false
	}
	if len(n) > 200 {
		return false
	}
	for _, r := range n {
		if unicode.IsControl(r) {
			return false
		}
	}
	return true
}

// Prepare normalizes and validates; empty input yields ok=false without error.
func Prepare(key string) (normalized string, ok bool) {
	n := Normalize(key)
	if n == "" {
		return "", false
	}
	if !Valid(n) {
		return "", false
	}
	return n, true
}

// ScopeKey builds a stable diagnostic key spanning endpoint and idempotency material.
func ScopeKey(endpointID, key string) string {
	return endpointID + ":" + Normalize(key)
}

// Equal reports whether two raw keys collide after normalization.
func Equal(a, b string) bool {
	return Normalize(a) != "" && Normalize(a) == Normalize(b)
}
