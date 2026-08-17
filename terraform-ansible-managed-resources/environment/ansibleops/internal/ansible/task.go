package ansible

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

type Task struct {
	Name   string
	Module string
	Args   map[string]any
	Vars   map[string]string
	Become bool
}

func (t Task) Validate() error {
	if strings.TrimSpace(t.Name) == "" {
		return fmt.Errorf("task name is required")
	}
	if strings.TrimSpace(t.Module) == "" {
		return fmt.Errorf("module is required")
	}
	if !strings.Contains(t.Module, ".") {
		return fmt.Errorf("module must use a fully qualified collection name: %s", t.Module)
	}
	return nil
}

func (t Task) Render(indent int) (string, error) {
	if err := t.Validate(); err != nil {
		return "", err
	}
	pad := strings.Repeat(" ", indent)
	var b strings.Builder
	b.WriteString(pad)
	b.WriteString("- name: ")
	b.WriteString(quote(t.Name))
	b.WriteByte('\n')
	if t.Become {
		b.WriteString(pad)
		b.WriteString("  become: true\n")
	}
	if len(t.Vars) > 0 {
		b.WriteString(pad)
		b.WriteString("  vars:\n")
		keys := sortedStringKeys(t.Vars)
		for _, key := range keys {
			b.WriteString(pad)
			b.WriteString("    ")
			b.WriteString(key)
			b.WriteString(": ")
			b.WriteString(quote(t.Vars[key]))
			b.WriteByte('\n')
		}
	}
	b.WriteString(pad)
	b.WriteString("  ")
	b.WriteString(t.Module)
	b.WriteString(":\n")
	keys := sortedAnyKeys(t.Args)
	for _, key := range keys {
		b.WriteString(renderKV(pad+"    ", key, t.Args[key]))
	}
	return b.String(), nil
}

func renderKV(indent, key string, value any) string {
	var b strings.Builder
	b.WriteString(indent)
	b.WriteString(key)
	b.WriteString(":")
	switch v := value.(type) {
	case nil:
		b.WriteString(" null\n")
	case string:
		b.WriteByte(' ')
		b.WriteString(quote(v))
		b.WriteByte('\n')
	case bool:
		if v {
			b.WriteString(" true\n")
		} else {
			b.WriteString(" false\n")
		}
	case int:
		b.WriteByte(' ')
		b.WriteString(strconv.Itoa(v))
		b.WriteByte('\n')
	case int64:
		b.WriteByte(' ')
		b.WriteString(strconv.FormatInt(v, 10))
		b.WriteByte('\n')
	case []string:
		b.WriteByte('\n')
		for _, item := range v {
			b.WriteString(indent)
			b.WriteString("  - ")
			b.WriteString(quote(item))
			b.WriteByte('\n')
		}
	case map[string]string:
		b.WriteByte('\n')
		for _, child := range sortedStringKeys(v) {
			b.WriteString(indent)
			b.WriteString("  ")
			b.WriteString(child)
			b.WriteString(": ")
			b.WriteString(quote(v[child]))
			b.WriteByte('\n')
		}
	default:
		b.WriteByte(' ')
		b.WriteString(quote(fmt.Sprint(value)))
		b.WriteByte('\n')
	}
	return b.String()
}

func quote(value string) string {
	value = strings.ReplaceAll(value, "\\", "\\\\")
	value = strings.ReplaceAll(value, "\"", "\\\"")
	value = strings.ReplaceAll(value, "\n", "\\n")
	value = strings.ReplaceAll(value, "\r", "\\r")
	value = strings.ReplaceAll(value, "\t", "\\t")
	return "\"" + value + "\""
}

func sortedAnyKeys(values map[string]any) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortedStringKeys(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
