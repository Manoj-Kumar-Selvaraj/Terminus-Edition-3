package config

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	rt "edge-router/internal/runtime"
)

type ValidationError struct {
	Path string `json:"path"`
	Message string `json:"message"`
}

func (e ValidationError) Error() string {
	if e.Path == "" {
		return e.Message
	}
	return e.Path + ": " + e.Message
}

type ValidationResult struct {
	State rt.DesiredState `json:"state"`
	Errors []ValidationError `json:"errors,omitempty"`
}

type UpdateStatus string

const (
	StatusAccepted UpdateStatus = "accepted"
	StatusRejected UpdateStatus = "rejected"
	StatusDuplicate UpdateStatus = "duplicate"
	StatusStale UpdateStatus = "stale"
	StatusConflict UpdateStatus = "conflict"
)

type UpdateEnvelope struct {
	Snapshot rt.SourceSnapshot
	Digest string
	ReceivedAt time.Time
	Result chan UpdateResult
}

type UpdateResult struct {
	Status UpdateStatus `json:"status"`
	Source string `json:"source"`
	Revision int64 `json:"revision"`
	Generation uint64 `json:"generation,omitempty"`
	Message string `json:"message,omitempty"`
}

type AcceptedSource struct {
	Snapshot rt.SourceSnapshot
	Digest string
}

type Ingress struct {
	mu sync.Mutex
	queue chan UpdateEnvelope
	accepted map[string]AcceptedSource
	pending map[string]UpdateEnvelope
	globalHighest int64
	closed bool
}

func NewIngress(capacity int) *Ingress {
	if capacity < 1 {
		capacity = 16
	}
	return &Ingress{
		queue: make(chan UpdateEnvelope, capacity),
		accepted: make(map[string]AcceptedSource),
		pending: make(map[string]UpdateEnvelope),
	}
}

func (i *Ingress) Submit(ctx context.Context, snapshot rt.SourceSnapshot) (<-chan UpdateResult, error) {
	if strings.TrimSpace(snapshot.Source) == "" {
		return nil, errors.New("source is required")
	}
	if snapshot.Revision < 1 {
		return nil, errors.New("revision must be positive")
	}
	payload, err := canonicalSourcePayload(snapshot)
	if err != nil {
		return nil, err
	}
	envelope := UpdateEnvelope{
		Snapshot: snapshot,
		Digest: rt.SemanticDigest(payload),
		ReceivedAt: time.Now().UTC(),
		Result: make(chan UpdateResult, 1),
	}
	i.mu.Lock()
	if i.closed {
		i.mu.Unlock()
		return nil, errors.New("configuration ingress is closed")
	}
	if snapshot.Revision < i.globalHighest {
		i.mu.Unlock()
		envelope.Result <- UpdateResult{Status: StatusStale, Source: snapshot.Source, Revision: snapshot.Revision, Message: "revision is older than accepted revision"}
		close(envelope.Result)
		return envelope.Result, nil
	}
	if accepted, ok := i.accepted[snapshot.Source]; ok {
		if snapshot.Revision < accepted.Snapshot.Revision {
			i.mu.Unlock()
			envelope.Result <- UpdateResult{Status: StatusStale, Source: snapshot.Source, Revision: snapshot.Revision, Message: "revision is stale"}
			close(envelope.Result)
			return envelope.Result, nil
		}
		if snapshot.Revision == accepted.Snapshot.Revision && envelope.Digest == accepted.Digest {
			i.mu.Unlock()
			envelope.Result <- UpdateResult{Status: StatusDuplicate, Source: snapshot.Source, Revision: snapshot.Revision}
			close(envelope.Result)
			return envelope.Result, nil
		}
	}
	if old, ok := i.pending[snapshot.Source]; ok {
		if old.Snapshot.Revision <= snapshot.Revision {
			i.mu.Unlock()
			old.Result <- UpdateResult{Status: StatusDuplicate, Source: old.Snapshot.Source, Revision: old.Snapshot.Revision, Message: "coalesced by queued source update"}
			close(old.Result)
			return envelope.Result, nil
		}
	}
	i.pending[snapshot.Source] = envelope
	i.mu.Unlock()

	select {
	case i.queue <- envelope:
		return envelope.Result, nil
	default:
		return i.coalesceFullQueue(envelope)
	case <-ctx.Done():
		i.mu.Lock()
		delete(i.pending, snapshot.Source)
		i.mu.Unlock()
		return nil, ctx.Err()
	}
}

func (i *Ingress) coalesceFullQueue(envelope UpdateEnvelope) (<-chan UpdateResult, error) {
	i.mu.Lock()
	defer i.mu.Unlock()
	if old, ok := i.pending[envelope.Snapshot.Source]; ok {
		if old.Snapshot.Revision <= envelope.Snapshot.Revision {
			return envelope.Result, nil
		}
	}
	i.pending[envelope.Snapshot.Source] = envelope
	return envelope.Result, nil
}

func (i *Ingress) Next(ctx context.Context) (UpdateEnvelope, error) {
	select {
	case envelope, ok := <-i.queue:
		if !ok {
			return UpdateEnvelope{}, io.EOF
		}
		i.mu.Lock()
		if pending, exists := i.pending[envelope.Snapshot.Source]; exists && pending.Snapshot.Revision == envelope.Snapshot.Revision {
			delete(i.pending, envelope.Snapshot.Source)
		}
		i.mu.Unlock()
		return envelope, nil
	case <-ctx.Done():
		return UpdateEnvelope{}, ctx.Err()
	}
}

func (i *Ingress) MergeCandidate(envelope UpdateEnvelope) rt.DesiredState {
	i.mu.Lock()
	defer i.mu.Unlock()
	i.accepted[envelope.Snapshot.Source] = AcceptedSource{Snapshot: envelope.Snapshot, Digest: envelope.Digest}
	if envelope.Snapshot.Revision > i.globalHighest {
		i.globalHighest = envelope.Snapshot.Revision
	}
	sources := make([]string, 0, len(i.accepted))
	for source := range i.accepted {
		sources = append(sources, source)
	}
	sort.Strings(sources)
	state := rt.DesiredState{
		SchemaVersion: 1,
		SourceRevisions: make(map[string]int64),
		SourceDigests: make(map[string]string),
	}
	for _, source := range sources {
		accepted := i.accepted[source]
		state.Routes = append(state.Routes, accepted.Snapshot.Routes...)
		state.Pools = mergePools(state.Pools, accepted.Snapshot.Pools)
		state.SourceRevisions[source] = accepted.Snapshot.Revision
		state.SourceDigests[source] = accepted.Digest
	}
	return state
}

func (i *Ingress) InstallRecoveredSources(revisions map[string]int64, digests map[string]string) {
	i.mu.Lock()
	defer i.mu.Unlock()
	for source, revision := range revisions {
		if revision > i.globalHighest {
			i.globalHighest = revision
		}
		entry := i.accepted[source]
		entry.Snapshot.Source = source
		entry.Snapshot.Revision = revision
		entry.Digest = digests[source]
		i.accepted[source] = entry
	}
}

func (i *Ingress) AcceptedRevisions() map[string]int64 {
	i.mu.Lock()
	defer i.mu.Unlock()
	out := make(map[string]int64, len(i.accepted))
	for source, accepted := range i.accepted {
		out[source] = accepted.Snapshot.Revision
	}
	return out
}

func (i *Ingress) Close() {
	i.mu.Lock()
	defer i.mu.Unlock()
	if !i.closed {
		close(i.queue)
		i.closed = true
	}
}

func mergePools(base []rt.PoolSpec, additions []rt.PoolSpec) []rt.PoolSpec {
	index := make(map[string]int, len(base)+len(additions))
	out := append([]rt.PoolSpec(nil), base...)
	for idx, pool := range out {
		index[pool.ID] = idx
	}
	for _, pool := range additions {
		if idx, ok := index[pool.ID]; ok {
			out[idx] = pool
		} else {
			index[pool.ID] = len(out)
			out = append(out, pool)
		}
	}
	return out
}

func canonicalSourcePayload(snapshot rt.SourceSnapshot) (any, error) {
	copySnapshot := snapshot
	copySnapshot.ObservedAt = ""
	return copySnapshot, nil
}

func ParseFile(path string) (rt.DesiredState, error) {
	file, err := os.Open(path)
	if err != nil {
		return rt.DesiredState{}, err
	}
	defer file.Close()
	return Parse(file)
}

func Parse(reader io.Reader) (rt.DesiredState, error) {
	decoder := json.NewDecoder(io.LimitReader(reader, 16<<20))
	decoder.DisallowUnknownFields()
	var state rt.DesiredState
	if err := decoder.Decode(&state); err != nil {
		return rt.DesiredState{}, fmt.Errorf("decode configuration: %w", err)
	}
	if decoder.More() {
		return rt.DesiredState{}, errors.New("multiple JSON values are not allowed")
	}
	return Normalize(state), nil
}

func ParseSource(reader io.Reader) (rt.SourceSnapshot, error) {
	decoder := json.NewDecoder(io.LimitReader(reader, 8<<20))
	decoder.DisallowUnknownFields()
	var snapshot rt.SourceSnapshot
	if err := decoder.Decode(&snapshot); err != nil {
		return rt.SourceSnapshot{}, fmt.Errorf("decode source snapshot: %w", err)
	}
	return snapshot, nil
}

func Normalize(state rt.DesiredState) rt.DesiredState {
	out := state
	out.Routes = append([]rt.RouteSpec(nil), state.Routes...)
	out.Pools = append([]rt.PoolSpec(nil), state.Pools...)
	for routeIndex := range out.Routes {
		route := &out.Routes[routeIndex]
		route.ID = strings.TrimSpace(route.ID)
		route.PoolID = strings.TrimSpace(route.PoolID)
		route.Match.Host = strings.ToLower(strings.TrimSpace(route.Match.Host))
		route.Match.PathPrefix = normalizePath(route.Match.PathPrefix)
		for methodIndex := range route.Match.Methods {
			route.Match.Methods[methodIndex] = strings.ToUpper(strings.TrimSpace(route.Match.Methods[methodIndex]))
		}
		sort.Strings(route.Match.Methods)
	}
	for poolIndex := range out.Pools {
		pool := &out.Pools[poolIndex]
		pool.ID = strings.TrimSpace(pool.ID)
		pool.Selection.Mode = strings.ToLower(strings.TrimSpace(pool.Selection.Mode))
		for endpointIndex := range pool.Endpoints {
			endpoint := &pool.Endpoints[endpointIndex]
			endpoint.Address = strings.TrimSpace(endpoint.Address)
			if endpoint.Transport == "" {
				endpoint.Transport = "http"
			}
		}
	}
	return out
}

func normalizePath(path string) string {
	path = strings.TrimSpace(path)
	if path == "" {
		return "/"
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	for strings.Contains(path, "//") {
		path = strings.ReplaceAll(path, "//", "/")
	}
	return path
}

func Validate(state rt.DesiredState) ValidationResult {
	state = Normalize(state)
	result := ValidationResult{State: state}
	if state.SchemaVersion != 1 {
		result.Errors = append(result.Errors, ValidationError{Path: "schema_version", Message: "must equal 1"})
	}
	if len(state.Routes) == 0 {
		result.Errors = append(result.Errors, ValidationError{Path: "routes", Message: "at least one route is required"})
	}
	if len(state.Pools) == 0 {
		result.Errors = append(result.Errors, ValidationError{Path: "pools", Message: "at least one pool is required"})
	}
	poolIDs := make(map[string]struct{}, len(state.Pools))
	for poolIndex, pool := range state.Pools {
		path := fmt.Sprintf("pools[%d]", poolIndex)
		if pool.ID == "" {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".id", Message: "pool id is required"})
		}
		if _, exists := poolIDs[pool.ID]; exists {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".id", Message: "duplicate pool id"})
		}
		poolIDs[pool.ID] = struct{}{}
		validatePool(path, pool, &result)
	}
	routeIDs := make(map[string]struct{}, len(state.Routes))
	for routeIndex, route := range state.Routes {
		path := fmt.Sprintf("routes[%d]", routeIndex)
		if route.ID == "" {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".id", Message: "route id is required"})
		}
		if _, exists := routeIDs[route.ID]; exists {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".id", Message: "duplicate route id"})
		}
		routeIDs[route.ID] = struct{}{}
		if _, exists := poolIDs[route.PoolID]; !exists {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".pool_id", Message: "referenced pool does not exist"})
		}
		if route.Match.PathPrefix == "" {
			result.Errors = append(result.Errors, ValidationError{Path: path + ".match.path_prefix", Message: "path prefix is required"})
		}
		for methodIndex, method := range route.Match.Methods {
			if method == "" {
				result.Errors = append(result.Errors, ValidationError{Path: fmt.Sprintf("%s.match.methods[%d]", path, methodIndex), Message: "empty method"})
			}
		}
	}
	return result
}

func validatePool(path string, pool rt.PoolSpec, result *ValidationResult) {
	if len(pool.Endpoints) == 0 {
		result.Errors = append(result.Errors, ValidationError{Path: path + ".endpoints", Message: "pool needs at least one endpoint"})
	}
	if pool.Selection.Mode == "" {
		result.Errors = append(result.Errors, ValidationError{Path: path + ".selection.mode", Message: "selection mode is required"})
	}
	if pool.Retry.MaxAttempts < 1 || pool.Retry.MaxAttempts > 8 {
		result.Errors = append(result.Errors, ValidationError{Path: path + ".retry.max_attempts", Message: "must be between 1 and 8"})
	}
	if pool.Drain.TimeoutMillis < 10 || pool.Drain.TimeoutMillis > 300000 {
		result.Errors = append(result.Errors, ValidationError{Path: path + ".drain.timeout_millis", Message: "must be between 10 and 300000"})
	}
	addresses := make(map[string]struct{}, len(pool.Endpoints))
	for endpointIndex, endpoint := range pool.Endpoints {
		epPath := fmt.Sprintf("%s.endpoints[%d]", path, endpointIndex)
		if endpoint.Address == "" {
			result.Errors = append(result.Errors, ValidationError{Path: epPath + ".address", Message: "address is required"})
		}
		if endpoint.Weight < 1 || endpoint.Weight > 1000 {
			result.Errors = append(result.Errors, ValidationError{Path: epPath + ".weight", Message: "weight must be 1..1000"})
		}
		if _, exists := addresses[endpoint.Address]; exists {
			result.Errors = append(result.Errors, ValidationError{Path: epPath + ".address", Message: "duplicate endpoint address"})
		}
		addresses[endpoint.Address] = struct{}{}
	}
}

func ValidationErrors(result ValidationResult) error {
	if len(result.Errors) == 0 {
		return nil
	}
	var buffer bytes.Buffer
	for index, item := range result.Errors {
		if index > 0 {
			buffer.WriteString("; ")
		}
		buffer.WriteString(item.Error())
	}
	return errors.New(buffer.String())
}
