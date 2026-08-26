package catalog

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"sovereign-lb/internal/model"
)

type Scenario struct {
	Name        string        `json:"name"`
	Description string        `json:"description"`
	Desired     model.Desired `json:"desired"`
}

type Summary struct {
	Name           string `json:"name"`
	Description    string `json:"description"`
	Revision       uint64 `json:"revision"`
	ListenerCount  int    `json:"listener_count"`
	TargetCount    int    `json:"target_count"`
	PrepareQuorum  int    `json:"prepare_quorum"`
	ActivateQuorum int    `json:"activate_quorum"`
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
	sort.Slice(result, func(i, j int) bool { return result[i].Name < result[j].Name })
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

func Summarize(scenario Scenario) Summary {
	targets := 0
	for _, group := range scenario.Desired.TargetGroups {
		targets += len(group.Targets)
	}
	return Summary{
		Name:           scenario.Name,
		Description:    scenario.Description,
		Revision:       scenario.Desired.Revision,
		ListenerCount:  len(scenario.Desired.Listeners),
		TargetCount:    targets,
		PrepareQuorum:  scenario.Desired.Rollout.PrepareQuorum,
		ActivateQuorum: scenario.Desired.Rollout.ActivateQuorum,
	}
}

func Find(scenarios []Scenario, name string) (Scenario, bool) {
	for _, scenario := range scenarios {
		if scenario.Name == name {
			return scenario, true
		}
	}
	return Scenario{}, false
}

func Summaries(scenarios []Scenario) []Summary {
	result := make([]Summary, 0, len(scenarios))
	for _, scenario := range scenarios {
		result = append(result, Summarize(scenario))
	}
	return result
}
