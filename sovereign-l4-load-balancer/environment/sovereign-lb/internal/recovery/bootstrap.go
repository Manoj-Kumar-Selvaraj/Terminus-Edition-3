package recovery

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"sovereign-lb/internal/model"
	"sovereign-lb/internal/persistence"
	"sovereign-lb/internal/revision"
	"sovereign-lb/internal/snapshot"
)

type Bootstrap struct {
	Root       string
	Repository *snapshot.Repository
	Revisions  *revision.Store
}

type Report struct {
	AcceptedRevision uint64 `json:"accepted_revision"`
	ActiveGeneration uint64 `json:"active_generation"`
	RecoveredCurrent bool   `json:"recovered_current"`
	FallbackUsed     bool   `json:"fallback_used"`
	GenerationCount  int    `json:"generation_count"`
}

func Open(root string) (*Bootstrap, error) {
	if err := os.MkdirAll(filepath.Join(root, "generations"), 0750); err != nil {
		return nil, err
	}
	revisions, err := revision.Open(root)
	if err != nil {
		return nil, err
	}
	repository := snapshot.NewRepository(filepath.Join(root, "generations"))
	return &Bootstrap{Root: root, Repository: repository, Revisions: revisions}, nil
}

func (bootstrap *Bootstrap) Recover() (Report, error) {
	report := Report{AcceptedRevision: bootstrap.Revisions.AcceptedRevision()}
	generations, err := bootstrap.Repository.Generations()
	if err != nil {
		return report, err
	}
	report.GenerationCount = len(generations)
	current, currentErr := bootstrap.Repository.Current()
	if currentErr == nil {
		report.ActiveGeneration = current.Snapshot.Generation
		report.RecoveredCurrent = true
		return report, nil
	}
	if len(generations) == 0 {
		return report, nil
	}
	latest := generations[len(generations)-1]
	if err := bootstrap.Repository.SetCurrent(latest); err != nil {
		return report, fmt.Errorf("activate fallback generation: %w", err)
	}
	report.ActiveGeneration = latest
	report.FallbackUsed = true
	return report, nil
}

func (bootstrap *Bootstrap) ValidateAuthority() error {
	path := filepath.Join(bootstrap.Root, "authority.json")
	var state struct {
		AcceptedRevision uint64 `json:"accepted_revision"`
		NextGeneration   uint64 `json:"next_generation"`
	}
	if err := persistence.ReadJSON(path, &state); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	if state.NextGeneration == 0 {
		return fmt.Errorf("authority next_generation is invalid")
	}
	if state.AcceptedRevision == 0 {
		return nil
	}
	generations, err := bootstrap.Repository.Generations()
	if err != nil {
		return err
	}
	for _, generation := range generations {
		compiled, loadErr := bootstrap.Repository.Load(generation)
		if loadErr != nil {
			continue
		}
		if compiled.Snapshot.Revision > state.AcceptedRevision {
			return fmt.Errorf("generation %d revision exceeds accepted authority", generation)
		}
	}
	return nil
}

func (bootstrap *Bootstrap) LoadDesired(path string) (model.Desired, error) {
	var desired model.Desired
	if err := persistence.ReadJSON(path, &desired); err != nil {
		return model.Desired{}, err
	}
	if err := model.ValidateDesired(desired); err != nil {
		return model.Desired{}, err
	}
	return desired, nil
}

func CurrentPointer(root string) (uint64, error) {
	data, err := os.ReadFile(filepath.Join(root, "generations", "CURRENT"))
	if err != nil {
		return 0, err
	}
	value := strings.TrimSpace(string(data))
	if value == "" {
		return 0, fmt.Errorf("CURRENT is empty")
	}
	var generation uint64
	if _, err := fmt.Sscanf(value, "%d", &generation); err != nil {
		return 0, fmt.Errorf("CURRENT is not numeric")
	}
	return generation, nil
}
