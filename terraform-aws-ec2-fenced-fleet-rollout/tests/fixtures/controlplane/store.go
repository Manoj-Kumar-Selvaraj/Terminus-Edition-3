package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

type Value map[string]any

type snapshot struct {
	Owner string
	State Value
}

type store struct {
	mu      sync.Mutex
	path    string
	logPath string
	state   Value
	log     []snapshot
}

func loadValue(path string) (Value, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Value{}, nil
		}
		return nil, err
	}
	result := Value{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func atomicWrite(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	tmp, err := os.CreateTemp(filepath.Dir(path), filepath.Base(path)+".")
	if err != nil {
		return err
	}
	name := tmp.Name()
	defer os.Remove(name)
	if _, err := tmp.Write(data); err == nil {
		err = tmp.Sync()
	}
	if closeErr := tmp.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return err
	}
	return os.Rename(name, path)
}

func object(value any) Value {
	if result, ok := value.(Value); ok {
		return result
	}
	if result, ok := value.(map[string]any); ok {
		return result
	}
	return Value{}
}

func stringValue(value any) string {
	if value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}

func (s *store) persist() error {
	if err := atomicWrite(s.path, s.state); err != nil {
		return err
	}
	entries := make([]any, 0, len(s.log))
	for _, item := range s.log {
		entries = append(entries, Value{"owner": item.Owner, "state": item.State})
	}
	return atomicWrite(s.logPath, Value{"entries": entries})
}

func (s *store) ownerInProgress() string {
	refresh := object(object(s.state["autoscaling_group"])["instance_refresh"])
	if stringValue(refresh["status"]) != "in_progress" {
		return ""
	}
	return stringValue(refresh["owner_token"])
}
