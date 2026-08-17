package journalspec

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"fleetrollout/internal/stateio"
	"fleetrollout/internal/types"
)

func Repair(path string) ([]types.Value, types.Value, error) {
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []types.Value{}, types.Value{"truncated_tail": false, "preserved_records": 0}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	lines := strings.Split(strings.TrimSuffix(string(data), "\n"), "\n")
	records := []types.Value{}
	truncated := false
	for index, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		value := types.Value{}
		if err := json.Unmarshal([]byte(line), &value); err != nil {
			if index != len(lines)-1 {
				return nil, nil, fmt.Errorf("invalid interior journal record at line %d", index+1)
			}
			truncated = true
			continue
		}
		records = append(records, value)
	}
	if truncated {
		if err := rewrite(path, records); err != nil {
			return nil, nil, err
		}
	}
	return records, types.Value{"truncated_tail": truncated, "preserved_records": len(records)}, nil
}

func Append(path string, record types.Value) error {
	if err := os.MkdirAll(parent(path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer file.Close()
	data, _ := json.Marshal(record)
	if _, err := file.Write(append(data, '\n')); err != nil {
		return err
	}
	return file.Sync()
}

func rewrite(path string, records []types.Value) error {
	contents := []byte{}
	for _, record := range records {
		line, _ := json.Marshal(record)
		contents = append(contents, line...)
		contents = append(contents, '\n')
	}
	return os.WriteFile(path, contents, 0o644)
}

func parent(path string) string {
	return stateio.Dir(path)
}
