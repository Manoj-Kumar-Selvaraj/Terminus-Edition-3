package reconcile

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"edge-router/internal/checkpoint"
	"edge-router/internal/compiler"
	"edge-router/internal/config"
	rt "edge-router/internal/runtime"
)

type EventKind string

const (
	EventAccepted  EventKind = "accepted"
	EventRejected  EventKind = "rejected"
	EventDuplicate EventKind = "duplicate"
	EventStale     EventKind = "stale"
	EventConflict  EventKind = "conflict"
)

type Event struct {
	Kind       EventKind `json:"kind"`
	Source     string    `json:"source"`
	Revision   int64     `json:"revision"`
	Generation uint64    `json:"generation"`
	Digest     string    `json:"digest,omitempty"`
	Message    string    `json:"message,omitempty"`
	At         time.Time `json:"at"`
}

type Status struct {
	Generation        uint64            `json:"generation"`
	AcceptedRevisions map[string]int64  `json:"accepted_revisions"`
	AcceptedDigests   map[string]string `json:"accepted_digests"`
	LastEvent         Event             `json:"last_event"`
	Ready             bool              `json:"ready"`
}

type Reconciler struct {
	mu                sync.Mutex
	ingress           *config.Ingress
	compiler          *compiler.Compiler
	store             *rt.PublicationStore
	checkpoints       *checkpoint.Store
	registry          *rt.Registry
	generation        atomic.Uint64
	acceptedRevisions map[string]int64
	acceptedDigests   map[string]string
	lastEvent         Event
	ready             atomic.Bool
	onPublish         func(previous, current *rt.RuntimeSnapshot)
}

func New(ingress *config.Ingress, compiler *compiler.Compiler, store *rt.PublicationStore, checkpoints *checkpoint.Store, registry *rt.Registry) *Reconciler {
	return &Reconciler{
		ingress:           ingress,
		compiler:          compiler,
		store:             store,
		checkpoints:       checkpoints,
		registry:          registry,
		acceptedRevisions: make(map[string]int64),
		acceptedDigests:   make(map[string]string),
	}
}

func (r *Reconciler) SetPublishHook(hook func(previous, current *rt.RuntimeSnapshot)) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.onPublish = hook
}

func (r *Reconciler) Run(ctx context.Context) error {
	for {
		envelope, err := r.ingress.Next(ctx)
		if err != nil {
			if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
				return nil
			}
			return err
		}
		result := r.Apply(ctx, envelope)
		envelope.Result <- result
		close(envelope.Result)
	}
}

func (r *Reconciler) Apply(ctx context.Context, envelope config.UpdateEnvelope) config.UpdateResult {
	source := envelope.Snapshot.Source
	revision := envelope.Snapshot.Revision
	r.mu.Lock()
	acceptedRevision := r.acceptedRevisions[source]
	acceptedDigest := r.acceptedDigests[source]
	if revision < acceptedRevision {
		r.recordLocked(Event{Kind: EventStale, Source: source, Revision: revision, Digest: envelope.Digest, Message: "revision is stale"})
		r.mu.Unlock()
		return config.UpdateResult{Status: config.StatusStale, Source: source, Revision: revision, Generation: r.generation.Load()}
	}
	if revision == acceptedRevision && revision != 0 {
		if acceptedDigest == envelope.Digest || acceptedDigest == "" {
			r.recordLocked(Event{Kind: EventDuplicate, Source: source, Revision: revision, Digest: envelope.Digest})
			r.mu.Unlock()
			return config.UpdateResult{Status: config.StatusDuplicate, Source: source, Revision: revision, Generation: r.generation.Load()}
		}
		r.recordLocked(Event{Kind: EventConflict, Source: source, Revision: revision, Digest: envelope.Digest, Message: "same revision already observed"})
		r.mu.Unlock()
		return config.UpdateResult{Status: config.StatusDuplicate, Source: source, Revision: revision, Generation: r.generation.Load()}
	}
	r.mu.Unlock()

	candidate := r.ingress.MergeCandidate(envelope)
	validation := config.Validate(candidate)
	if err := config.ValidationErrors(validation); err != nil {
		generation := r.generation.Add(1)
		r.mu.Lock()
		r.acceptedRevisions[source] = revision
		r.recordLocked(Event{Kind: EventRejected, Source: source, Revision: revision, Generation: generation, Digest: envelope.Digest, Message: err.Error()})
		r.mu.Unlock()
		return config.UpdateResult{Status: config.StatusRejected, Source: source, Revision: revision, Generation: generation, Message: err.Error()}
	}

	generation := r.generation.Add(1)
	snapshot, err := r.compiler.Compile(validation.State, generation)
	if err != nil {
		r.mu.Lock()
		r.acceptedRevisions[source] = revision
		r.recordLocked(Event{Kind: EventRejected, Source: source, Revision: revision, Generation: generation, Digest: envelope.Digest, Message: err.Error()})
		r.mu.Unlock()
		return config.UpdateResult{Status: config.StatusRejected, Source: source, Revision: revision, Generation: generation, Message: err.Error()}
	}

	if ctx.Err() != nil {
		return config.UpdateResult{Status: config.StatusRejected, Source: source, Revision: revision, Generation: generation, Message: ctx.Err().Error()}
	}

	body, err := r.checkpoints.Prepare(snapshot)
	if err != nil {
		return config.UpdateResult{Status: config.StatusRejected, Source: source, Revision: revision, Generation: generation, Message: err.Error()}
	}
	if err := r.checkpoints.Commit(body); err != nil {
		return config.UpdateResult{Status: config.StatusRejected, Source: source, Revision: revision, Generation: generation, Message: err.Error()}
	}

	previous := r.store.Current()
	r.store.Publish(snapshot)
	r.applyRemovalLifecycle(previous, snapshot)

	r.mu.Lock()
	r.acceptedRevisions[source] = revision
	r.acceptedDigests[source] = envelope.Digest
	r.recordLocked(Event{Kind: EventAccepted, Source: source, Revision: revision, Generation: generation, Digest: envelope.Digest})
	hook := r.onPublish
	r.ready.Store(true)
	r.mu.Unlock()
	if hook != nil {
		hook(previous, snapshot)
	}
	return config.UpdateResult{Status: config.StatusAccepted, Source: source, Revision: revision, Generation: generation}
}

func (r *Reconciler) applyRemovalLifecycle(previous, current *rt.RuntimeSnapshot) {
	if previous == nil || current == nil {
		return
	}
	currentIDs := make(map[string]struct{})
	for _, pool := range current.Pools {
		for _, endpoint := range pool.Endpoints {
			currentIDs[endpoint.Identity] = struct{}{}
		}
	}
	for _, pool := range previous.Pools {
		for _, endpoint := range pool.Endpoints {
			if _, exists := currentIDs[endpoint.Identity]; exists || endpoint.Runtime == nil {
				continue
			}
			deadline := time.Now().UTC().Add(time.Duration(pool.Drain.TimeoutMillis) * time.Millisecond)
			endpoint.Runtime.MarkDraining(deadline)
			endpoint.Runtime.Retire()
		}
	}
}

func (r *Reconciler) Recover(body checkpoint.Body) (*rt.RuntimeSnapshot, error) {
	if body.Generation == 0 {
		return nil, errors.New("checkpoint generation is zero")
	}
	snapshot, err := r.compiler.Compile(body.Desired, body.Generation)
	if err != nil {
		return nil, err
	}
	snapshot.SourceRevisions = rt.CloneRevisions(body.SourceRevisions)
	snapshot.SourceDigests = rt.CloneDigests(body.SourceDigests)
	r.store.Publish(snapshot)
	r.generation.Store(body.Generation)
	r.mu.Lock()
	r.acceptedRevisions = rt.CloneRevisions(body.SourceRevisions)
	r.acceptedDigests = rt.CloneDigests(body.SourceDigests)
	r.ready.Store(true)
	r.recordLocked(Event{Kind: EventAccepted, Source: "recovery", Revision: int64(body.Generation), Generation: body.Generation, Message: "restored checkpoint"})
	r.mu.Unlock()
	return snapshot, nil
}

func (r *Reconciler) Bootstrap(state rt.DesiredState) (*rt.RuntimeSnapshot, error) {
	validation := config.Validate(state)
	if err := config.ValidationErrors(validation); err != nil {
		return nil, err
	}
	generation := r.generation.Add(1)
	snapshot, err := r.compiler.Compile(validation.State, generation)
	if err != nil {
		return nil, err
	}
	r.store.Publish(snapshot)
	r.mu.Lock()
	r.acceptedRevisions = rt.CloneRevisions(state.SourceRevisions)
	r.acceptedDigests = rt.CloneDigests(state.SourceDigests)
	r.ready.Store(true)
	r.recordLocked(Event{Kind: EventAccepted, Source: "bootstrap", Revision: int64(generation), Generation: generation, Message: "bootstrap configuration published"})
	r.mu.Unlock()
	return snapshot, nil
}

func (r *Reconciler) Status() Status {
	r.mu.Lock()
	defer r.mu.Unlock()
	return Status{
		Generation:        r.generation.Load(),
		AcceptedRevisions: rt.CloneRevisions(r.acceptedRevisions),
		AcceptedDigests:   rt.CloneDigests(r.acceptedDigests),
		LastEvent:         r.lastEvent,
		Ready:             r.ready.Load(),
	}
}

func (r *Reconciler) SetReady(ready bool) {
	r.ready.Store(ready)
}

func (r *Reconciler) Generation() uint64 {
	return r.generation.Load()
}

func (r *Reconciler) recordLocked(event Event) {
	if event.At.IsZero() {
		event.At = time.Now().UTC()
	}
	if event.Generation == 0 {
		event.Generation = r.generation.Load()
	}
	r.lastEvent = event
}

func DiffEndpoints(previous, current *rt.RuntimeSnapshot) (added, removed, retained []string) {
	previousIDs := snapshotEndpointIDs(previous)
	currentIDs := snapshotEndpointIDs(current)
	for id := range currentIDs {
		if _, exists := previousIDs[id]; exists {
			retained = append(retained, id)
		} else {
			added = append(added, id)
		}
	}
	for id := range previousIDs {
		if _, exists := currentIDs[id]; !exists {
			removed = append(removed, id)
		}
	}
	sort.Strings(added)
	sort.Strings(removed)
	sort.Strings(retained)
	return
}

func snapshotEndpointIDs(snapshot *rt.RuntimeSnapshot) map[string]struct{} {
	out := make(map[string]struct{})
	if snapshot == nil {
		return out
	}
	for poolID, pool := range snapshot.Pools {
		for _, endpoint := range pool.Endpoints {
			out[fmt.Sprintf("%s/%s", poolID, endpoint.Identity)] = struct{}{}
		}
	}
	return out
}
