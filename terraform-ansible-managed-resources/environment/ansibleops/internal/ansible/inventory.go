package ansible

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

type InventorySummary struct {
	Path        string
	Groups      []string
	HostLines   int
	ManagedSeen bool
	LocalSeen   bool
}

func InspectInventory(path string) (InventorySummary, error) {
	summary := InventorySummary{Path: path}
	f, err := os.Open(path)
	if err != nil {
		return summary, fmt.Errorf("open inventory %s: %w", path, err)
	}
	defer f.Close()

	currentGroup := ""
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			currentGroup = strings.TrimSuffix(strings.TrimPrefix(line, "["), "]")
			if !strings.Contains(currentGroup, ":") {
				summary.Groups = append(summary.Groups, currentGroup)
			}
			if currentGroup == "managed" {
				summary.ManagedSeen = true
			}
			continue
		}
		if currentGroup == "" || strings.Contains(currentGroup, ":vars") || strings.Contains(currentGroup, ":children") {
			continue
		}
		summary.HostLines++
		fields := strings.Fields(line)
		if len(fields) > 0 && (fields[0] == "localhost" || fields[0] == "127.0.0.1") {
			summary.LocalSeen = true
		}
	}
	if err := scanner.Err(); err != nil {
		return summary, fmt.Errorf("scan inventory %s: %w", path, err)
	}
	return summary, nil
}

func ValidateManagedInventory(path string) error {
	summary, err := InspectInventory(path)
	if err != nil {
		return err
	}
	if !summary.ManagedSeen {
		return fmt.Errorf("inventory %s does not define the [managed] group", path)
	}
	if summary.HostLines == 0 {
		return fmt.Errorf("inventory %s does not contain managed hosts", path)
	}
	return nil
}
