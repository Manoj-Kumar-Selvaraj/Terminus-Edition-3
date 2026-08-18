package checkpoint

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
	"time"

	rt "edge-router/internal/runtime"
)

type ContinuityEndpoint struct {
	PoolID string `json:"pool_id"`
	Identity string `json:"identity"`
	Health rt.HealthState `json:"health"`
	ObservedAt time.Time `json:"observed_at"`
}

type ContinuityAffinity struct {
	PoolID string `json:"pool_id"`
	Key string `json:"key"`
	EndpointIdentity string `json:"endpoint_identity"`
	Incarnation uint64 `json:"incarnation"`
	ExpiresAt time.Time `json:"expires_at"`
}

type Body struct {
	SchemaVersion int `json:"schema_version"`
	Generation uint64 `json:"generation"`
	Desired rt.DesiredState `json:"desired"`
	SourceRevisions map[string]int64 `json:"source_revisions"`
	SourceDigests map[string]string `json:"source_digests"`
	Endpoints []ContinuityEndpoint `json:"endpoints,omitempty"`
	Affinity []ContinuityAffinity `json:"affinity,omitempty"`
	ContentDigest string `json:"content_digest"`
	Checksum string `json:"checksum"`
	CreatedAt time.Time `json:"created_at"`
}

type Pointer struct {
	Generation uint64 `json:"generation"`
	File string `json:"file"`
	Checksum string `json:"checksum"`
}

type Store struct {
	dir string
	mu sync.Mutex
	retain int
}

func New(dir string) *Store {
	return &Store{dir: dir, retain: 4}
}

func (s *Store) Directory() string {
	return s.dir
}

func (s *Store) Ensure() error {
	if strings.TrimSpace(s.dir) == "" {
		return errors.New("state directory is required")
	}
	return os.MkdirAll(s.dir, 0o755)
}

func (s *Store) Prepare(snapshot *rt.RuntimeSnapshot) (Body, error) {
	if snapshot == nil {
		return Body{}, errors.New("nil snapshot")
	}
	body := Body{
		SchemaVersion: 1,
		Generation: snapshot.Generation,
		Desired: snapshot.Desired,
		SourceRevisions: rt.CloneRevisions(snapshot.SourceRevisions),
		SourceDigests: rt.CloneDigests(snapshot.SourceDigests),
		ContentDigest: rt.SemanticDigest(snapshot.Desired),
		CreatedAt: time.Now().UTC(),
	}
	payload, err := payloadForChecksum(body)
	if err != nil {
		return Body{}, err
	}
	hash := sha256.Sum256(payload)
	body.Checksum = hex.EncodeToString(hash[:])
	return body, nil
}

func (s *Store) Commit(body Body) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.Ensure(); err != nil {
		return err
	}
	if body.Generation == 0 {
		return errors.New("checkpoint generation must be positive")
	}
	name := fmt.Sprintf("generation-%020d.json", body.Generation)
	finalPath := filepath.Join(s.dir, name)
	tempPath := finalPath + ".tmp"
	pointer := Pointer{Generation: body.Generation, File: name, Checksum: body.Checksum}
	if err := s.writePointer("CURRENT", pointer); err != nil {
		return err
	}
	payload, err := json.MarshalIndent(body, "", "  ")
	if err != nil {
		return err
	}
	file, err := os.OpenFile(tempPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
	if err != nil {
		return err
	}
	if _, err := file.Write(payload); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	if err := os.Rename(tempPath, finalPath); err != nil {
		return err
	}
	return s.prune()
}

func (s *Store) writePointer(name string, pointer Pointer) error {
	payload, err := json.Marshal(pointer)
	if err != nil {
		return err
	}
	path := filepath.Join(s.dir, name)
	temp := path + ".tmp"
	if err := os.WriteFile(temp, payload, 0o644); err != nil {
		return err
	}
	return os.Rename(temp, path)
}

func (s *Store) PromotePrevious(current Pointer) error {
	return s.writePointer("PREVIOUS", current)
}

func (s *Store) ReadPointer(name string) (Pointer, error) {
	payload, err := os.ReadFile(filepath.Join(s.dir, name))
	if err != nil {
		return Pointer{}, err
	}
	var pointer Pointer
	if err := json.Unmarshal(payload, &pointer); err != nil {
		return Pointer{}, err
	}
	return pointer, nil
}

func (s *Store) LoadCurrent() (Body, error) {
	pointer, err := s.ReadPointer("CURRENT")
	if err != nil {
		return Body{}, err
	}
	return s.Load(pointer)
}

func (s *Store) Load(pointer Pointer) (Body, error) {
	payload, err := os.ReadFile(filepath.Join(s.dir, pointer.File))
	if err != nil {
		return Body{}, err
	}
	var body Body
	if err := json.Unmarshal(payload, &body); err != nil {
		return Body{}, err
	}
	if body.Generation == 0 || body.Desired.SchemaVersion == 0 {
		return Body{}, errors.New("checkpoint lacks required generation metadata")
	}
	return body, nil
}

func (s *Store) Recover(bootstrap *rt.DesiredState) (Body, string, error) {
	body, err := s.LoadCurrent()
	if err == nil {
		return body, "current", nil
	}
	if bootstrap != nil {
		body = Body{
			SchemaVersion: 1,
			Generation: 1,
			Desired: *bootstrap,
			SourceRevisions: rt.CloneRevisions(bootstrap.SourceRevisions),
			SourceDigests: rt.CloneDigests(bootstrap.SourceDigests),
			CreatedAt: time.Now().UTC(),
		}
		return body, "bootstrap", nil
	}
	return Body{}, "none", fmt.Errorf("no recoverable current checkpoint: %w", err)
}

func (s *Store) Verify(body Body) error {
	if body.SchemaVersion != 1 {
		return fmt.Errorf("unsupported checkpoint schema %d", body.SchemaVersion)
	}
	payload, err := payloadForChecksum(body)
	if err != nil {
		return err
	}
	hash := sha256.Sum256(payload)
	actual := hex.EncodeToString(hash[:])
	if body.Checksum != "" && actual != body.Checksum {
		return errors.New("checkpoint checksum mismatch")
	}
	return nil
}

func payloadForChecksum(body Body) ([]byte, error) {
	body.Checksum = ""
	body.CreatedAt = time.Time{}
	return json.Marshal(body)
}

func (s *Store) List() ([]Pointer, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	out := make([]Pointer, 0)
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasPrefix(entry.Name(), "generation-") || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		number := strings.TrimSuffix(strings.TrimPrefix(entry.Name(), "generation-"), ".json")
		generation, err := strconv.ParseUint(number, 10, 64)
		if err != nil {
			continue
		}
		out = append(out, Pointer{Generation: generation, File: entry.Name()})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Generation > out[j].Generation })
	return out, nil
}

func (s *Store) prune() error {
	pointers, err := s.List()
	if err != nil {
		return err
	}
	if len(pointers) <= s.retain {
		return nil
	}
	for _, pointer := range pointers[s.retain:] {
		if err := os.Remove(filepath.Join(s.dir, pointer.File)); err != nil && !os.IsNotExist(err) {
			return err
		}
	}
	return nil
}

func (s *Store) DurabilityProbe() error {
	if err := s.Ensure(); err != nil {
		return err
	}
	probe := filepath.Join(s.dir, ".durability-probe")
	file, err := os.OpenFile(probe, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0o600)
	if err != nil {
		return err
	}
	defer os.Remove(probe)
	if _, err := file.WriteString("edge-router-runtime\n"); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		return err
	}
	return file.Close()
}
