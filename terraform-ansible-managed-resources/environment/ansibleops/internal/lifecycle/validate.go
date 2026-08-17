package lifecycle

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
)

var unixNamePattern = regexp.MustCompile(`^[a-z_][a-z0-9_-]*[$]?$`)

func ValidateUnixName(kind, name string) error {
	name = strings.TrimSpace(name)
	if name == "" {
		return fmt.Errorf("%s name must not be empty", kind)
	}
	if len(name) > 32 {
		return fmt.Errorf("%s name %q exceeds 32 characters", kind, name)
	}
	if !unixNamePattern.MatchString(name) {
		return fmt.Errorf("%s name %q is not a portable local account name", kind, name)
	}
	return nil
}

func ValidateAbsolutePath(field, value string) error {
	value = strings.TrimSpace(value)
	if value == "" {
		return fmt.Errorf("%s must not be empty", field)
	}
	if strings.ContainsRune(value, '\x00') {
		return fmt.Errorf("%s contains NUL", field)
	}
	if !filepath.IsAbs(value) {
		return fmt.Errorf("%s must be absolute: %s", field, value)
	}
	return nil
}

func ValidateCronExpressionPart(field, value string) error {
	value = NormalizeCronPart(value)
	if strings.ContainsAny(value, "\r\n\x00") {
		return fmt.Errorf("cron %s contains control characters", field)
	}
	if strings.Contains(value, " ") || strings.Contains(value, "\t") {
		return fmt.Errorf("cron %s must be one crontab field", field)
	}
	if len(value) > 64 {
		return fmt.Errorf("cron %s is unreasonably long", field)
	}
	return nil
}

func ValidateCronJob(job string) error {
	if strings.TrimSpace(job) == "" {
		return fmt.Errorf("cron job must not be empty")
	}
	if strings.ContainsRune(job, '\x00') {
		return fmt.Errorf("cron job contains NUL")
	}
	if strings.ContainsAny(job, "\r\n") {
		return fmt.Errorf("cron job must be a single logical line")
	}
	return nil
}

func ValidateLine(line string) error {
	if strings.ContainsRune(line, '\x00') {
		return fmt.Errorf("managed line contains NUL")
	}
	if strings.ContainsAny(line, "\r\n") {
		return fmt.Errorf("managed line must not contain a newline")
	}
	return nil
}

func ValidateBlockMarker(marker string) error {
	if marker == "" {
		return nil
	}
	if strings.ContainsRune(marker, '\x00') {
		return fmt.Errorf("block marker contains NUL")
	}
	if !strings.Contains(marker, "{mark}") {
		return fmt.Errorf("block marker must contain {mark}")
	}
	return nil
}
