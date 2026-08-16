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
