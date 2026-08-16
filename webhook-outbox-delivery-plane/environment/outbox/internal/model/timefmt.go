package model

import "time"

const RFC3339Milli = "2006-01-02T15:04:05.000Z07:00"

func FormatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339Nano)
}

func ParseTime(s string) (time.Time, error) {
	if s == "" {
		return time.Time{}, nil
	}
	layouts := []string{time.RFC3339Nano, time.RFC3339, RFC3339Milli}
	var err error
	for _, layout := range layouts {
		var t time.Time
		t, err = time.Parse(layout, s)
		if err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, err
}

func PtrTime(t time.Time) *time.Time {
	u := t.UTC()
	return &u
}

func PtrString(s string) *string {
	if s == "" {
		return nil
	}
	v := s
	return &v
}

func DerefString(p *string) string {
	if p == nil {
		return ""
	}
	return *p
}
