package snapshot

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
	"time"

	"sovereign-lb/internal/model"
)

type Compiled struct {
	Snapshot  model.Snapshot
	Canonical []byte
	Digest    string
}

func Compile(desired model.Desired, generation uint64, created time.Time) (Compiled, error) {
	if err := model.ValidateDesired(desired); err != nil { return Compiled{}, err }
	listeners := append([]model.Listener(nil), desired.Listeners...)
	groups := append([]model.TargetGroup(nil), desired.TargetGroups...)
	sort.Slice(listeners, func(i, j int) bool { return listeners[i].Name < listeners[j].Name })
	for index := range groups {
		groups[index].Targets = append([]model.Target(nil), groups[index].Targets...)
		sort.Slice(groups[index].Targets, func(i, j int) bool {
			if groups[index].Targets[i].ID == groups[index].Targets[j].ID { return groups[index].Targets[i].Incarnation < groups[index].Targets[j].Incarnation }
			return groups[index].Targets[i].ID < groups[index].Targets[j].ID
		})
	}
	sort.Slice(groups, func(i, j int) bool { return groups[i].Name < groups[j].Name })
	value := model.Snapshot{Generation: generation, Revision: desired.Revision, CreatedAt: created.UTC().Format(time.RFC3339Nano), Listeners: listeners, TargetGroups: groups, Limits: desired.Limits}
	canonical, err := marshalCanonical(value)
	if err != nil { return Compiled{}, err }
	digest := sha256.Sum256(canonical)
	return Compiled{Snapshot: value, Canonical: canonical, Digest: hex.EncodeToString(digest[:])}, nil
}

func marshalCanonical(value any) ([]byte, error) {
	data, err := json.Marshal(value)
	if err != nil { return nil, err }
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	var generic any
	if err := decoder.Decode(&generic); err != nil { return nil, err }
	var output bytes.Buffer
	if err := writeCanonical(&output, generic); err != nil { return nil, err }
	return output.Bytes(), nil
}

func writeCanonical(output *bytes.Buffer, value any) error {
	switch typed := value.(type) {
	case nil: output.WriteString("null")
	case bool: if typed { output.WriteString("true") } else { output.WriteString("false") }
	case string: encoded, _ := json.Marshal(typed); output.Write(encoded)
	case json.Number: output.WriteString(typed.String())
	case []any:
		output.WriteByte('[')
		for index, item := range typed { if index > 0 { output.WriteByte(',') }; if err := writeCanonical(output, item); err != nil { return err } }
		output.WriteByte(']')
	case map[string]any:
		keys := make([]string, 0, len(typed)); for key := range typed { keys = append(keys, key) }; sort.Strings(keys)
		output.WriteByte('{')
		for index, key := range keys { if index > 0 { output.WriteByte(',') }; encoded, _ := json.Marshal(key); output.Write(encoded); output.WriteByte(':'); if err := writeCanonical(output, typed[key]); err != nil { return err } }
		output.WriteByte('}')
	default: return &json.UnsupportedTypeError{Type: nil}
	}
	return nil
}