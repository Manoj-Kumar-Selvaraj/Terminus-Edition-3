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
		vb, err := json.Marshal(v[k])
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

func MustMarshalObject(v map[string]any) []byte {
	b, err := MarshalObject(v)
	if err != nil {
		panic(fmt.Sprintf("canonicaljson: %v", err))
	}
	return b
}
