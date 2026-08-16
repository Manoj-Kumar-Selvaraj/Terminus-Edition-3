package payload

import (
	"bytes"
	"encoding/json"
)

// Compact re-encodes JSON maps with sorted-stable encoding via encoding/json defaults.
func Compact(raw []byte) ([]byte, error) {
	var v any
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if err := dec.Decode(&v); err != nil {
		return nil, err
	}
	return json.Marshal(v)
}

func MustCompact(raw []byte) []byte {
	b, err := Compact(raw)
	if err != nil {
		return raw
	}
	return b
}

func IsObject(raw []byte) bool {
	raw = bytes.TrimSpace(raw)
	return len(raw) > 0 && raw[0] == '{'
}

// Size returns compacted byte length, or len(raw) when compact fails.
func Size(raw []byte) int {
	b, err := Compact(raw)
	if err != nil {
		return len(raw)
	}
	return len(b)
}

// AsObjectMap decodes a JSON object payload into a generic map.
func AsObjectMap(raw []byte) (map[string]any, error) {
	if !IsObject(raw) {
		return nil, errNotObject{}
	}
	var m map[string]any
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if err := dec.Decode(&m); err != nil {
		return nil, err
	}
	return m, nil
}

type errNotObject struct{}

func (errNotObject) Error() string { return "invalid_payload" }
