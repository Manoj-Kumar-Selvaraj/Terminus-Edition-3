package lifecycle

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

func NormalizeMode(value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", nil
	}
	trimmed := strings.TrimPrefix(value, "0")
	if trimmed == "" {
		trimmed = "0"
	}
	parsed, err := strconv.ParseUint(trimmed, 8, 32)
	if err != nil || parsed > 0o7777 {
		return "", fmt.Errorf("invalid file mode %q", value)
	}
	return fmt.Sprintf("%04o", parsed), nil
}

func ModeEqual(left, right string) bool {
	l, lerr := NormalizeMode(left)
	r, rerr := NormalizeMode(right)
	return lerr == nil && rerr == nil && l == r
}

func NormalizeCronPart(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "*"
	}
	return value
}

func CanonicalGroups(groups []string) []string {
	out := make([]string, 0, len(groups))
	seen := map[string]struct{}{}
	for _, group := range groups {
		group = strings.TrimSpace(group)
		if group == "" {
			continue
		}
		if _, ok := seen[group]; ok {
			continue
		}
		seen[group] = struct{}{}
		out = append(out, group)
	}
	sort.Strings(out)
	return out
}
