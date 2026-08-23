package registry

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"enterprise-pii/internal/model"
)

type SourceRegistry struct {
	mu sync.RWMutex
	sources map[string]model.Source
}

func NewSourceRegistry() *SourceRegistry { return &SourceRegistry{sources: map[string]model.Source{}} }

func (r *SourceRegistry) Register(source model.Source) (model.Source, error) {
	if source.ID == "" || source.Root == "" || source.Department == "" || source.Region == "" { return model.Source{}, errors.New("source identity and ownership are required") }
	root, err := filepath.Abs(filepath.Clean(source.Root))
	if err != nil { return model.Source{}, err }
	resolved, err := filepath.EvalSymlinks(root)
	if err != nil { resolved = root }
	source.CanonicalRoot = filepath.Clean(resolved)
	r.mu.Lock()
	defer r.mu.Unlock()
	if existing, ok := r.sources[source.ID]; ok && existing.CanonicalRoot != source.CanonicalRoot { return model.Source{}, errors.New("source id conflict") }
	for id, existing := range r.sources {
		if id != source.ID && strings.EqualFold(existing.CanonicalRoot, source.CanonicalRoot) { return model.Source{}, errors.New("canonical source already registered") }
	}
	r.sources[source.ID] = source
	return source, nil
}

func (r *SourceRegistry) Get(id string) (model.Source, bool) { r.mu.RLock(); defer r.mu.RUnlock(); v, ok := r.sources[id]; return v, ok }
func (r *SourceRegistry) List() []model.Source {
	r.mu.RLock(); defer r.mu.RUnlock()
	out := make([]model.Source, 0, len(r.sources))
	for _, source := range r.sources { out = append(out, source) }
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

type PolicyRegistry struct {
	mu sync.RWMutex
	policies map[string]model.Policy
}

func NewPolicyRegistry() *PolicyRegistry { return &PolicyRegistry{policies: map[string]model.Policy{}} }

func CanonicalPolicyDigest(policy model.Policy) (string, error) {
	copy := policy
	copy.Digest = ""
	copy.PublishedAt = time.Time{}
	copy.Categories = append([]string(nil), copy.Categories...)
	sort.Strings(copy.Categories)
	body, err := json.Marshal(copy)
	if err != nil { return "", err }
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:]), nil
}

func (r *PolicyRegistry) Publish(policy model.Policy, now time.Time) (model.Policy, error) {
	if policy.Version == "" || policy.KeyEpoch == "" || policy.DetectorBundle == "" { return model.Policy{}, errors.New("policy identity is incomplete") }
	digest, err := CanonicalPolicyDigest(policy)
	if err != nil { return model.Policy{}, err }
	policy.Digest = digest
	policy.PublishedAt = now.UTC()
	r.mu.Lock()
	defer r.mu.Unlock()
	if existing, ok := r.policies[policy.Version]; ok {
		if existing.Digest != digest { return model.Policy{}, errors.New("immutable policy version conflict") }
		return existing, nil
	}
	r.policies[policy.Version] = policy
	return policy, nil
}

func (r *PolicyRegistry) Get(version string) (model.Policy, bool) { r.mu.RLock(); defer r.mu.RUnlock(); v, ok := r.policies[version]; return v, ok }
func (r *PolicyRegistry) List() []model.Policy {
	r.mu.RLock(); defer r.mu.RUnlock()
	out := make([]model.Policy, 0, len(r.policies))
	for _, policy := range r.policies { out = append(out, policy) }
	sort.Slice(out, func(i, j int) bool { return out[i].Version < out[j].Version })
	return out
}