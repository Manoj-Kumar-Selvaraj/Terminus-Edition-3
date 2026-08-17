package observe

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type CronState struct {
	Exists   bool
	Name     string
	User     string
	Minute   string
	Hour     string
	Day      string
	Month    string
	Weekday  string
	Job      string
	Disabled bool
}

func InspectCron(userName, entryName string) (CronState, error) {
	state := CronState{Name: entryName, User: userName}
	paths := []string{
		filepath.Join("/var/spool/cron/crontabs", userName),
		filepath.Join("/var/spool/cron", userName),
	}
	var f *os.File
	var err error
	for _, path := range paths {
		f, err = os.Open(path)
		if err == nil {
			break
		}
		if !os.IsNotExist(err) {
			return state, fmt.Errorf("open cron spool: %w", err)
		}
	}
	if f == nil {
		return state, nil
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	marker := "#Ansible: " + entryName
	foundMarker := false
	for scanner.Scan() {
		line := scanner.Text()
		if line == marker {
			foundMarker = true
			continue
		}
		if !foundMarker {
			continue
		}
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") && !strings.HasPrefix(trimmed, "#*") {
			continue
		}
		disabled := strings.HasPrefix(trimmed, "#")
		if disabled {
			trimmed = strings.TrimSpace(strings.TrimPrefix(trimmed, "#"))
		}
		parts := strings.Fields(trimmed)
		if len(parts) < 6 {
			return state, fmt.Errorf("cron entry %s has invalid field count", entryName)
		}
		state.Exists = true
		state.Minute = parts[0]
		state.Hour = parts[1]
		state.Day = parts[2]
		state.Month = parts[3]
		state.Weekday = parts[4]
		state.Job = strings.Join(parts[5:], " ")
		state.Disabled = disabled
		return state, nil
	}
	if err := scanner.Err(); err != nil {
		return state, fmt.Errorf("scan cron spool: %w", err)
	}
	return state, nil
}
