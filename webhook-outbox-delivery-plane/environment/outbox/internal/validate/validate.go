package validate

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"unicode/utf8"
)

var (
	ErrEmptyName    = errors.New("name_required")
	ErrEmptySlug    = errors.New("slug_required")
	ErrBadURL       = errors.New("invalid_url")
	ErrBadSecret    = errors.New("hmac_secret_required")
	ErrBadQuota     = errors.New("invalid_quota")
	ErrBadAttempts  = errors.New("invalid_max_attempts")
	ErrBadPayload   = errors.New("invalid_payload")
	ErrBadOwner     = errors.New("lease_owner_required")
	ErrBadOutcome   = errors.New("invalid_outcome")
)

func TenantName(name string) error {
	name = strings.TrimSpace(name)
	if name == "" || utf8.RuneCountInString(name) > 128 {
		return ErrEmptyName
	}
	return nil
}

func TenantSlug(slug string) error {
	slug = strings.TrimSpace(slug)
	if slug == "" || utf8.RuneCountInString(slug) > 64 {
		return ErrEmptySlug
	}
	for _, r := range slug {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '_' {
			continue
		}
		return fmt.Errorf("%w: charset", ErrEmptySlug)
	}
	return nil
}

func Quota(n int) error {
	if n < 1 || n > 1_000_000 {
		return ErrBadQuota
	}
	return nil
}

func EndpointURL(raw string) error {
	raw = strings.TrimSpace(raw)
	u, err := url.Parse(raw)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return ErrBadURL
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return ErrBadURL
	}
	return nil
}

func HMACSecret(secret string) error {
	if strings.TrimSpace(secret) == "" {
		return ErrBadSecret
	}
	return nil
}

func MaxAttempts(n int) error {
	if n < 1 || n > 100 {
		return ErrBadAttempts
	}
	return nil
}

func PayloadObject(v any) ([]byte, error) {
	if v == nil {
		return nil, ErrBadPayload
	}
	switch t := v.(type) {
	case map[string]any:
		b, err := json.Marshal(t)
		if err != nil {
			return nil, ErrBadPayload
		}
		return b, nil
	case json.RawMessage:
		if !json.Valid(t) {
			return nil, ErrBadPayload
		}
		var obj map[string]any
		if err := json.Unmarshal(t, &obj); err != nil {
			return nil, ErrBadPayload
		}
		return json.Marshal(obj)
	default:
		b, err := json.Marshal(v)
		if err != nil {
			return nil, ErrBadPayload
		}
		var obj map[string]any
		if err := json.Unmarshal(b, &obj); err != nil {
			return nil, ErrBadPayload
		}
		return json.Marshal(obj)
	}
}

func LeaseOwner(owner string) error {
	if strings.TrimSpace(owner) == "" {
		return ErrBadOwner
	}
	return nil
}

func Outcome(outcome string) error {
	switch outcome {
	case "delivered", "failed":
		return nil
	default:
		return ErrBadOutcome
	}
}
