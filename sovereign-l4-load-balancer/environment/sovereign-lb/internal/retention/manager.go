package retention

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"

	"sovereign-lb/internal/snapshot"
)

type Lease struct {
	Generation uint64
	Holder     string
}

type Manager struct {
	mutex      sync.Mutex
	repository *snapshot.Repository
	limit      int
	leases     map[uint64]map[string]struct{}
}

func New(repository *snapshot.Repository, limit int) *Manager {
	if limit < 1 {
		limit = 1
	}
	return &Manager{
		repository: repository,
		limit:      limit,
		leases:     map[uint64]map[string]struct{}{},
	}
}

func (manager *Manager) Acquire(generation uint64, holder string) {
	manager.mutex.Lock()
	defer manager.mutex.Unlock()
	holders := manager.leases[generation]
	if holders == nil {
		holders = map[string]struct{}{}
		manager.leases[generation] = holders
	}
	holders[holder] = struct{}{}
}

func (manager *Manager) Release(generation uint64, holder string) {
	manager.mutex.Lock()
	defer manager.mutex.Unlock()
	holders, ok := manager.leases[generation]
	if !ok {
		return
	}
	delete(holders, holder)
	if len(holders) == 0 {
		delete(manager.leases, generation)
	}
}

func (manager *Manager) Held(generation uint64) bool {
	manager.mutex.Lock()
	defer manager.mutex.Unlock()
	return len(manager.leases[generation]) > 0
}

func (manager *Manager) Collect(activeGeneration uint64) ([]uint64, error) {
	generations, err := manager.repository.Generations()
	if err != nil {
		return nil, err
	}
	if len(generations) <= manager.limit {
		return nil, nil
	}
	sort.Slice(generations, func(i, j int) bool { return generations[i] < generations[j] })
	removed := make([]uint64, 0)
	for _, generation := range generations {
		if len(generations)-len(removed) <= manager.limit {
			break
		}
		if generation == activeGeneration || manager.Held(generation) {
			continue
		}
		path := manager.repository.GenerationPath(generation)
		if err := os.RemoveAll(path); err != nil {
			return removed, fmt.Errorf("remove generation %d: %w", generation, err)
		}
		removed = append(removed, generation)
	}
	return removed, nil
}

func (manager *Manager) Snapshot() []Lease {
	manager.mutex.Lock()
	defer manager.mutex.Unlock()
	result := make([]Lease, 0)
	for generation, holders := range manager.leases {
		for holder := range holders {
			result = append(result, Lease{Generation: generation, Holder: holder})
		}
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].Generation == result[j].Generation {
			return result[i].Holder < result[j].Holder
		}
		return result[i].Generation < result[j].Generation
	})
	return result
}
