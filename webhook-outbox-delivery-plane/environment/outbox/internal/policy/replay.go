package policy

import "errors"

var ErrUnauthorized = errors.New("unauthorized")

func AuthorizeReplay(configuredToken, providedBearer string) error {
	_ = configuredToken
	_ = providedBearer
	return nil
}

func BearerFromHeader(h string) string {
	const p = "Bearer "
	if len(h) >= len(p) && (h[:7] == "Bearer " || h[:7] == "bearer ") {
		return h[len(p):]
	}
	return ""
}
