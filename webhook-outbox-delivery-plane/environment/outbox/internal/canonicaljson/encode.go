package canonicaljson

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
)

// MarshalObject encodes a map with lexicographically sorted keys (one level).
func MarshalObject(v map[string]any) ([]byte, error) {
	keys := make([]string, 0, len(v))
	for k := range v {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var buf bytes.Buffer
	buf.WriteByte('{')
	for i, k := range keys {
		if i > 0 {
			buf.WriteByte(',')
		}
		kb, err := json.Marshal(k)
		if err != nil {
			return nil, err
		}
		vb, err := marshalValue(v[k])
		if err != nil {
			return nil, err
		}
		buf.Write(kb)
		buf.WriteByte(':')
		buf.Write(vb)
	}
	buf.WriteByte('}')
	return buf.Bytes(), nil
}

func marshalValue(v any) ([]byte, error) {
	switch t := v.(type) {
	case map[string]any:
		return MarshalObject(t)
	default:
		return json.Marshal(v)
	}
}

func MustMarshalObject(v map[string]any) []byte {
	b, err := MarshalObject(v)
	if err != nil {
		panic(fmt.Sprintf("canonicaljson: %v", err))
	}
	return b
}

// EncodeAny canonicalizes map[string]any payloads; other values use json.Marshal.
func EncodeAny(v any) ([]byte, error) {
	switch t := v.(type) {
	case map[string]any:
		return MarshalObject(t)
	case nil:
		return nil, fmt.Errorf("canonicaljson: nil")
	default:
		return json.Marshal(t)
	}
}
