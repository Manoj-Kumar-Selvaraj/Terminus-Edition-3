package revision

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"path/filepath"
	"sync"

	"sovereign-lb/internal/persistence"
)

var ErrStale = errors.New("revision is not newer than accepted authority")
var ErrConflict = errors.New("idempotency key is bound to different content")

type Record struct { RequestDigest string `json:"request_digest"`; Revision uint64 `json:"revision"`; Generation uint64 `json:"generation"`; Response []byte `json:"response"` }
type state struct { AcceptedRevision uint64 `json:"accepted_revision"`; NextGeneration uint64 `json:"next_generation"`; Records map[string]Record `json:"records"` }
type Store struct { path string; mutex sync.Mutex; state state }

func Open(root string) (*Store, error) {
	store := &Store{path: filepath.Join(root, "authority.json"), state: state{NextGeneration: 1, Records: map[string]Record{}}}
	if err := persistence.ReadJSON(store.path, &store.state); err != nil && !errors.Is(err, os.ErrNotExist) { return nil, err }
	if store.state.NextGeneration == 0 { store.state.NextGeneration = 1 }
	if store.state.Records == nil { store.state.Records = map[string]Record{} }
	return store, nil
}

func Digest(body []byte) string { sum := sha256.Sum256(body); return hex.EncodeToString(sum[:]) }

func (store *Store) Begin(key string, revision uint64, requestDigest string) (uint64, *Record, error) {
	store.mutex.Lock(); defer store.mutex.Unlock()
	if existing, ok := store.state.Records[key]; ok {
		copy := existing; return existing.Generation, &copy, nil
	}
	if revision <= store.state.AcceptedRevision { return 0, nil, ErrStale }
	return store.state.NextGeneration, nil, nil
}

func (store *Store) Commit(key, requestDigest string, revision, generation uint64, response []byte) error {
	store.mutex.Lock(); defer store.mutex.Unlock()
	if revision <= store.state.AcceptedRevision || generation != store.state.NextGeneration { return ErrStale }
	next := store.state
	next.Records = cloneRecords(store.state.Records)
	next.AcceptedRevision = revision
	next.NextGeneration = generation + 1
	next.Records[key] = Record{RequestDigest: requestDigest, Revision: revision, Generation: generation, Response: append([]byte(nil), response...)}
	if err := persistence.WriteJSON(store.path, next); err != nil { return err }
	store.state = next
	return nil
}

func (store *Store) AcceptedRevision() uint64 { store.mutex.Lock(); defer store.mutex.Unlock(); return store.state.AcceptedRevision }
func cloneRecords(input map[string]Record) map[string]Record { output := make(map[string]Record, len(input)); for key, value := range input { output[key] = value }; return output }