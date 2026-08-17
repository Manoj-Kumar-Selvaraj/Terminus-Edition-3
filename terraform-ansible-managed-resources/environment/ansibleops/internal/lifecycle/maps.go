package lifecycle

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
)

func MapFingerprint(values map[string]string) string {
	var b strings.Builder
	for key, value := range values {
		b.WriteString(key)
		b.WriteByte('=')
		b.WriteString(value)
		b.WriteByte('\n')
	}
	h := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(h[:])
}
