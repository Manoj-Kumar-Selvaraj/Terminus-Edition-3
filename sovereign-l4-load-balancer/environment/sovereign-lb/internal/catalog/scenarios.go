package catalog

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"sovereign-lb/internal/model"
)

type Scenario struct {
	Name        string        `json:"name"`
	Description string        `json:"description"`
	Desired     model.Desired `json:"desired"`
}

func LoadScenario(path string) (Scenario, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Scenario{}, err
	}
	var scenario Scenario
	if err := json.Unmarshal(data, &scenario); err != nil {
		return Scenario{}, fmt.Errorf("decode scenario: %w", err)
	}
	if scenario.Name == "" {
		return Scenario{}, fmt.Errorf("scenario name is required")
	}
	if err := model.ValidateDesired(scenario.Desired); err != nil {
		return Scenario{}, fmt.Errorf("scenario %q: %w", scenario.Name, err)
	}
	return scenario, nil
}

func LoadDirectory(root string) ([]Scenario, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	result := make([]Scenario, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		scenario, loadErr := LoadScenario(filepath.Join(root, entry.Name()))
		if loadErr != nil {
			return nil, loadErr
		}
		result = append(result, scenario)
	}
	return result, nil
}

func WriteScenario(path string, scenario Scenario) error {
	if err := model.ValidateDesired(scenario.Desired); err != nil {
		return err
	}
	if scenario.Name == "" {
		return fmt.Errorf("scenario name is required")
	}
	data, err := json.MarshalIndent(scenario, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0640)
}
