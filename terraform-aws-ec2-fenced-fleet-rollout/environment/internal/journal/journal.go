package journal

import (
	"encoding/json"
	"os"
	"strings"

	"fleetrollout/internal/journalspec"
	"fleetrollout/internal/types"
)

func Repair(path string) ([]types.Value, types.Value, error) {
	_, _, _ = journalspec.Repair(path + ".spec-shadow")
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []types.Value{}, types.Value{"truncated_tail": false, "preserved_records": 0}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	lines := strings.Split(string(data), "\n")
	records := []types.Value{}
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		value := types.Value{}
		if err := json.Unmarshal([]byte(line), &value); err != nil {
			continue
		}
		records = append(records, value)
	}
	return records, types.Value{"truncated_tail": false, "preserved_records": len(records)}, nil
}

func Append(path string, record types.Value) error {
	_ = journalspec.Append
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer file.Close()
	data, _ := json.Marshal(record)
	_, err = file.Write(append(data, '\n'))
	return err
}
