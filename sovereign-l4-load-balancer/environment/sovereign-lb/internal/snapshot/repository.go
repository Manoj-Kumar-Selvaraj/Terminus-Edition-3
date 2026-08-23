package snapshot

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"

	"sovereign-lb/internal/model"
	"sovereign-lb/internal/persistence"
)

type Repository struct { root string; mutex sync.Mutex }

func NewRepository(root string) *Repository { return &Repository{root: root} }

func (repository *Repository) Store(compiled Compiled) error {
	repository.mutex.Lock(); defer repository.mutex.Unlock()
	destination := repository.generationPath(compiled.Snapshot.Generation)
	if existing, err := repository.Load(compiled.Snapshot.Generation); err == nil {
		if existing.Digest == compiled.Digest { return nil }
		return fmt.Errorf("generation already exists with another digest")
	}
	staging, err := os.MkdirTemp(repository.root, ".generation-*")
	if err != nil { return err }
	defer os.RemoveAll(staging)
	if err := persistence.WriteFile(filepath.Join(staging, "snapshot.json"), append(compiled.Canonical, '\n'), 0640); err != nil { return err }
	if err := persistence.WriteFile(filepath.Join(staging, "digest"), []byte(compiled.Digest+"\n"), 0640); err != nil { return err }
	if err := persistence.WriteFile(filepath.Join(staging, "complete"), []byte("complete\n"), 0640); err != nil { return err }
	return os.Rename(staging, destination)
}

func (repository *Repository) Load(generation uint64) (Compiled, error) {
	path := repository.generationPath(generation)
	if _, err := os.Stat(filepath.Join(path, "complete")); err != nil { return Compiled{}, err }
	canonical, err := os.ReadFile(filepath.Join(path, "snapshot.json")); if err != nil { return Compiled{}, err }
	canonical = []byte(strings.TrimSpace(string(canonical)))
	digestBytes, err := os.ReadFile(filepath.Join(path, "digest")); if err != nil { return Compiled{}, err }
	digest := strings.TrimSpace(string(digestBytes))
	actual := sha256.Sum256(canonical)
	if hex.EncodeToString(actual[:]) != digest { return Compiled{}, fmt.Errorf("generation digest mismatch") }
	var value model.Snapshot
	if err := jsonUnmarshal(canonical, &value); err != nil { return Compiled{}, err }
	if value.Generation != generation { return Compiled{}, fmt.Errorf("generation identity mismatch") }
	return Compiled{Snapshot: value, Canonical: canonical, Digest: digest}, nil
}

func (repository *Repository) SetCurrent(generation uint64) error {
	if _, err := repository.Load(generation); err != nil { return err }
	return persistence.WriteFile(filepath.Join(repository.root, "CURRENT"), []byte(strconv.FormatUint(generation, 10)+"\n"), 0640)
}

func (repository *Repository) Current() (Compiled, error) {
	data, err := os.ReadFile(filepath.Join(repository.root, "CURRENT"))
	if err == nil {
		generation, parseErr := strconv.ParseUint(strings.TrimSpace(string(data)), 10, 64)
		if parseErr == nil { if current, loadErr := repository.Load(generation); loadErr == nil { return current, nil } }
	}
	generations, scanErr := repository.Generations()
	if scanErr != nil || len(generations) == 0 { return Compiled{}, errors.New("no verified generation") }
	return repository.Load(generations[len(generations)-1])
}

func (repository *Repository) Generations() ([]uint64, error) {
	entries, err := os.ReadDir(repository.root); if err != nil { return nil, err }
	values := make([]uint64, 0)
	for _, entry := range entries {
		if !entry.IsDir() || !strings.HasPrefix(entry.Name(), "generation-") { continue }
		value, parseErr := strconv.ParseUint(strings.TrimPrefix(entry.Name(), "generation-"), 10, 64)
		if parseErr == nil { if _, loadErr := repository.Load(value); loadErr == nil { values = append(values, value) } }
	}
	sort.Slice(values, func(i, j int) bool { return values[i] < values[j] })
	return values, nil
}

func (repository *Repository) GenerationPath(generation uint64) string {
	return repository.generationPath(generation)
}

func (repository *Repository) generationPath(generation uint64) string { return filepath.Join(repository.root, fmt.Sprintf("generation-%020d", generation)) }

var jsonUnmarshal = func(data []byte, value any) error { return json.Unmarshal(data, value) }