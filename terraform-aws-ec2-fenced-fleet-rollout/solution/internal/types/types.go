package types

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// Value is the shared JSON document type for config and inventory.
type Value map[string]any

const (
	ConfigSchema  = "ec2-module-config.v2"
	StateSchema   = "ec2sim.aws.2"
	IPAMPath      = "/app/data/ipam.sqlite"
	PrivateApp    = "private_app"
	PilotThenWave = "pilot-then-wave"
)

var ManifestFields = []string{
	"manifest_version",
	"ami_id",
	"ami_owner_account_id",
	"architecture",
	"commit_sha",
	"build_id",
	"user_data_sha256",
}

func Canonical(value any) []byte {
	data, err := json.Marshal(value)
	if err != nil {
		return []byte("null")
	}
	return data
}

func CanonicalCompact(value any) []byte {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(value); err != nil {
		return []byte("null")
	}
	out := bytes.TrimSpace(buf.Bytes())
	return out
}

func Hash(value any, length int) string {
	digest := sha256.Sum256(Canonical(value))
	encoded := hex.EncodeToString(digest[:])
	if length > 0 && length < len(encoded) {
		return encoded[:length]
	}
	return encoded
}

func ManifestDigest(artifact Value) string {
	payload := Value{}
	for _, key := range ManifestFields {
		payload[key] = artifact[key]
	}
	return Hash(payload, 0)
}

func Clone(value any) any {
	data := Canonical(value)
	var result any
	_ = json.Unmarshal(data, &result)
	return result
}

func CloneValue(value Value) Value {
	if value == nil {
		return Value{}
	}
	cloned, _ := Clone(value).(map[string]any)
	if cloned == nil {
		return Value{}
	}
	return Value(cloned)
}

func Object(value any) Value {
	if result, ok := value.(Value); ok {
		return result
	}
	if result, ok := value.(map[string]any); ok {
		return result
	}
	return Value{}
}

func Objects(value any) []Value {
	list, _ := value.([]any)
	result := make([]Value, 0, len(list))
	for _, item := range list {
		result = append(result, Object(item))
	}
	return result
}

func AnyList(values []Value) []any {
	out := make([]any, len(values))
	for i, item := range values {
		out[i] = item
	}
	return out
}

func StringList(value any) []string {
	list, _ := value.([]any)
	result := make([]string, 0, len(list))
	for _, item := range list {
		result = append(result, String(item))
	}
	return result
}

func String(value any) string {
	if value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return fmt.Sprint(value)
}

func Int(value any) int {
	switch typed := value.(type) {
	case int:
		return typed
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	case json.Number:
		parsed, _ := typed.Int64()
		return int(parsed)
	case string:
		parsed, _ := strconv.Atoi(typed)
		return parsed
	default:
		return 0
	}
}

func Bool(value any) bool {
	result, _ := value.(bool)
	return result
}

func Identifier(prefix string, parts ...any) string {
	values := make([]string, 0, len(parts))
	for _, part := range parts {
		text := strings.ReplaceAll(String(part), "/", "_")
		text = strings.ReplaceAll(text, ":", "_")
		values = append(values, text)
	}
	return prefix + "-" + strings.Join(values, "-")
}

func Require(value any, name string, errors *[]string) {
	if value == nil || value == "" {
		*errors = append(*errors, name+" is required")
		return
	}
	if list, ok := value.([]any); ok && len(list) == 0 {
		*errors = append(*errors, name+" is required")
	}
}

func SortedCopy(values []string) []string {
	out := append([]string{}, values...)
	sort.Strings(out)
	return out
}

func UniqueStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		if seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func JoinErrors(errors []string) error {
	if len(errors) == 0 {
		return nil
	}
	return fmt.Errorf("%s", strings.Join(errors, "; "))
}

func Keys(value Value) []string {
	keys := make([]string, 0, len(value))
	for key := range value {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func DeepGet(value any, path ...string) any {
	current := value
	for _, key := range path {
		obj := Object(current)
		if obj == nil {
			return nil
		}
		current = obj[key]
	}
	return current
}

func WalkStrings(value any, visit func(string)) {
	switch typed := value.(type) {
	case string:
		visit(typed)
	case []any:
		for _, item := range typed {
			WalkStrings(item, visit)
		}
	case []string:
		for _, item := range typed {
			visit(item)
		}
	case map[string]any:
		for _, key := range Keys(Value(typed)) {
			WalkStrings(typed[key], visit)
		}
	case Value:
		for _, key := range Keys(typed) {
			WalkStrings(typed[key], visit)
		}
	}
}

func Merge(base Value, overlay Value) Value {
	result := CloneValue(base)
	for _, key := range Keys(overlay) {
		result[key] = overlay[key]
	}
	return result
}

func IntOr(value any, fallback int) int {
	if value == nil {
		return fallback
	}
	parsed := Int(value)
	if parsed == 0 && String(value) == "" && fmt.Sprint(value) != "0" {
		return fallback
	}
	return parsed
}

