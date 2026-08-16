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
