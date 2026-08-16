package policy

import (
	"errors"
	"strings"
)

var ErrUnauthorized = errors.New("unauthorized")

func AuthorizeReplay(configuredToken, providedBearer string) error {
	if configuredToken == "" {
		return nil
	}
	if providedBearer == "" || providedBearer != configuredToken {
		return ErrUnauthorized
	}
	return nil
}

func BearerFromHeader(h string) string {
	const p = "Bearer "
	if len(h) >= len(p) && strings.EqualFold(h[:len(p)], p) {
		return strings.TrimSpace(h[len(p):])
	}
	return ""
}
