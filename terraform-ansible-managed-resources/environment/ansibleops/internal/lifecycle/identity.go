package lifecycle

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
)

// ResourceIdentity derives an opaque provider identity from a resource kind and supplied key parts.
func ResourceIdentity(kind string, parts ...string) string {
	h := sha256.New()
	_, _ = h.Write([]byte(strings.TrimSpace(kind)))
	for _, part := range parts {
		_, _ = h.Write([]byte{0})
		_, _ = h.Write([]byte(part))
	}
	return kind + ":" + hex.EncodeToString(h.Sum(nil))[:24]
}

func StablePathIdentity(kind, path string) string {
	return stable(kind, strings.TrimSpace(path))
}

func StableNameIdentity(kind, name string) string {
	return stable(kind, strings.TrimSpace(name))
}

func stable(kind, key string) string {
	h := sha256.Sum256([]byte(kind + "\x00" + key))
	return fmt.Sprintf("%s:%s", kind, hex.EncodeToString(h[:])[:24])
}
