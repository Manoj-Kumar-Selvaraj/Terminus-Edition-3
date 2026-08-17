package lifecycle

import (
	"fmt"
	"sort"
	"strings"
)

type Change struct {
	Field  string
	Before string
	After  string
}

type ChangeSet struct {
	changes []Change
}

func NewChangeSet() *ChangeSet {
	return &ChangeSet{}
}

func (s *ChangeSet) String(field, before, after string) {
	if before == after {
		return
	}
	s.changes = append(s.changes, Change{Field: field, Before: before, After: after})
}

func (s *ChangeSet) Mode(field, before, after string) {
	left, leftErr := NormalizeMode(before)
	right, rightErr := NormalizeMode(after)
	if leftErr != nil || rightErr != nil {
		s.String(field, before, after)
		return
	}
	if left != right {
		s.changes = append(s.changes, Change{Field: field, Before: left, After: right})
	}
}

func (s *ChangeSet) Strings(field string, before, after []string) {
	left := canonicalSlice(before)
	right := canonicalSlice(after)
	if strings.Join(left, "\x00") == strings.Join(right, "\x00") {
		return
	}
	s.changes = append(s.changes, Change{
		Field:  field,
		Before: strings.Join(left, ","),
		After:  strings.Join(right, ","),
	})
}

func (s *ChangeSet) Empty() bool {
	return len(s.changes) == 0
}

func (s *ChangeSet) Len() int {
	return len(s.changes)
}

func (s *ChangeSet) Changes() []Change {
	out := make([]Change, len(s.changes))
	copy(out, s.changes)
	return out
}

func (s *ChangeSet) Fields() []string {
	fields := make([]string, 0, len(s.changes))
	for _, change := range s.changes {
		fields = append(fields, change.Field)
	}
	return fields
}

func (s *ChangeSet) Summary() string {
	if s.Empty() {
		return "no changes"
	}
	parts := make([]string, 0, len(s.changes))
	for _, change := range s.changes {
		parts = append(parts, fmt.Sprintf("%s:%q->%q", change.Field, change.Before, change.After))
	}
	return strings.Join(parts, "; ")
}

func canonicalSlice(values []string) []string {
	seen := map[string]struct{}{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

type PathDesired struct {
	Path  string
	Mode  string
	Owner string
	Group string
}

func DiffPath(before, after PathDesired) *ChangeSet {
	set := NewChangeSet()
	set.String("path", before.Path, after.Path)
	set.Mode("mode", before.Mode, after.Mode)
	set.String("owner", before.Owner, after.Owner)
	set.String("group", before.Group, after.Group)
	return set
}

type CronDesired struct {
	Name     string
	User     string
	Minute   string
	Hour     string
	Day      string
	Month    string
	Weekday  string
	Job      string
	Disabled bool
}

func DiffCron(before, after CronDesired) *ChangeSet {
	set := NewChangeSet()
	set.String("name", before.Name, after.Name)
	set.String("user", before.User, after.User)
	set.String("minute", NormalizeCronPart(before.Minute), NormalizeCronPart(after.Minute))
	set.String("hour", NormalizeCronPart(before.Hour), NormalizeCronPart(after.Hour))
	set.String("day", NormalizeCronPart(before.Day), NormalizeCronPart(after.Day))
	set.String("month", NormalizeCronPart(before.Month), NormalizeCronPart(after.Month))
	set.String("weekday", NormalizeCronPart(before.Weekday), NormalizeCronPart(after.Weekday))
	set.String("job", before.Job, after.Job)
	set.String("disabled", fmt.Sprint(before.Disabled), fmt.Sprint(after.Disabled))
	return set
}
