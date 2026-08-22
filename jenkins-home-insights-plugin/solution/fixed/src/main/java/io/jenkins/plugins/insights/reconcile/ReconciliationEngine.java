package io.jenkins.plugins.insights.reconcile;

import io.jenkins.plugins.insights.model.Domain.*;
import io.jenkins.plugins.insights.source.HomeSources.ScanContext;
import io.jenkins.plugins.insights.source.HomeSources.ScanResult;
import io.jenkins.plugins.insights.source.HomeSources.SourceAdapter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

public final class ReconciliationEngine {
    private static final String DELETE_FENCE = "DELETE_FENCE";
    public record ReconcileResult(Snapshot snapshot, int scannedRecords, int appliedEvents,
                                  int rejectedEvents, boolean cancelled, Set<SourceKind> completedSources) {}

    private final List<SourceAdapter<? extends CanonicalRecord>> adapters;
    private final AtomicBoolean stopping;

    public ReconciliationEngine(List<SourceAdapter<? extends CanonicalRecord>> adapters, AtomicBoolean stopping) {
        this.adapters = List.copyOf(adapters); this.stopping = Objects.requireNonNull(stopping, "stopping");
    }

    public ReconcileResult full(ScanContext context) throws IOException {
        MutableState state = new MutableState(Snapshot.empty()); Set<SourceKind> completed = EnumSet.noneOf(SourceKind.class);
        int scanned = 0;
        for (SourceAdapter<? extends CanonicalRecord> adapter : adapters) {
            if (stopping.get()) return finish(state, scanned, 0, 0, true, completed);
            ScanResult<? extends CanonicalRecord> result = adapter.scan(context);
            state.replace(result.source(), result.records()); scanned += result.records().size();
            state.clearErrors(result.source()); state.errors.addAll(result.errors());
            if (result.supported()) state.unsupported.remove(result.source()); else state.unsupported.add(result.source());
            completed.add(result.source());
        }
        state.checkpoint = new Checkpoint(context.sequence(), "", "");
        return finish(state, scanned, 0, 0, false, completed);
    }

    public ReconcileResult incremental(Snapshot base, Collection<Event> events) {
        MutableState state = new MutableState(base); Set<SourceKind> touched = EnumSet.noneOf(SourceKind.class);
        int applied = 0; int rejected = 0; long checkpoint = base.checkpoint().appliedSequence();
        Map<String, String> represented = new HashMap<>();
        List<Event> ordered = events.stream().sorted(Comparator.comparingLong(Event::sequence).thenComparing(Event::eventId)).toList();
        for (Event event : ordered) {
            if (stopping.get()) return finish(state, 0, applied, rejected, true, touched);
            if (event.sequence() <= checkpoint) continue;
            if (event.sequence() != checkpoint + 1) { rejected++; break; }
            String signature = event.source() + ":" + event.operation() + ":" + event.recordKey() + ":" + event.payloadHash();
            String previous = represented.putIfAbsent(event.eventId(), signature);
            if (previous != null) { if (!previous.equals(signature)) rejected++; break; }
            try {
                if (!apply(state, event)) { rejected++; break; }
                checkpoint = event.sequence(); applied++; touched.add(event.source());
            } catch (RuntimeException invalid) {
                rejected++; state.errors.add(new SourceError(event.source(), event.recordKey(), "EVENT_REJECTED",
                        invalid.getMessage() == null ? invalid.getClass().getSimpleName() : invalid.getMessage()));
                break;
            }
        }
        state.checkpoint = new Checkpoint(checkpoint, base.checkpoint().generationId(), base.checkpoint().digest());
        return finish(state, 0, applied, rejected, false, touched);
    }

    private boolean apply(MutableState state, Event event) {
        long fence = state.fence(event.source(), event.recordKey());
        if (event.sequence() <= fence) return true;
        Map<String, CanonicalRecord> target = state.map(event.source());
        CanonicalRecord existing = target.get(event.recordKey());
        if (existing != null && event.sequence() <= existing.observedSequence()) return true;
        if (event.operation() == EventOperation.DELETE) {
            if (existing instanceof BuildRecord build && state.referencesBuild(event.recordKey())) {
                target.put(event.recordKey(), new BuildRecord(build.identity(), build.jobKey(), build.number(),
                        build.startedMillis(), build.durationMillis(), build.result(), RecordState.DELETED,
                        build.artifactIds(), event.sequence()));
            } else {
                target.remove(event.recordKey());
            }
            state.putFence(event.source(), event.recordKey(), event.sequence()); return true;
        }
        if (event.operation() == EventOperation.DIRTY) return true;
        Map<String, Object> payload = merge(existing, event.payload());
        CanonicalRecord record = RecordCodec.decode(event.source(), payload, event.sequence());
        if (!record.key().equals(event.recordKey())) throw new IllegalArgumentException("event key does not match payload key");
        target.put(event.recordKey(), record); state.removeFence(event.source(), event.recordKey()); return true;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> merge(CanonicalRecord existing, Map<String, Object> eventPayload) {
        if (existing == null) return eventPayload;
        Map<String, Object> payload = new LinkedHashMap<>(existing.toMap());
        Map<String, Object> identity = (Map<String, Object>) payload.remove("identity");
        payload.put("key", identity.get("key"));
        payload.put("displayName", identity.get("display"));
        payload.put("parentKey", identity.get("parent"));
        payload.putAll(eventPayload);
        return payload;
    }

    private ReconcileResult finish(MutableState state, int scanned, int applied, int rejected,
                                   boolean cancelled, Set<SourceKind> completed) {
        return new ReconcileResult(state.snapshot(), scanned, applied, rejected, cancelled,
                completed.isEmpty() ? Set.of() : EnumSet.copyOf(completed));
    }

    private static final class MutableState {
        private final Map<String, CanonicalRecord> jobs = new LinkedHashMap<>();
        private final Map<String, CanonicalRecord> builds = new LinkedHashMap<>();
        private final Map<String, CanonicalRecord> queue = new LinkedHashMap<>();
        private final Map<String, CanonicalRecord> nodes = new LinkedHashMap<>();
        private final Map<String, CanonicalRecord> fingerprints = new LinkedHashMap<>();
        private final Map<String, CanonicalRecord> plugins = new LinkedHashMap<>();
        private final List<SourceError> errors = new ArrayList<>();
        private final Set<SourceKind> unsupported = EnumSet.noneOf(SourceKind.class);
        private Checkpoint checkpoint;

        private MutableState(Snapshot base) {
            jobs.putAll(base.jobs()); builds.putAll(base.builds()); queue.putAll(base.queue()); nodes.putAll(base.nodes());
            fingerprints.putAll(base.fingerprints()); plugins.putAll(base.plugins()); errors.addAll(base.errors());
            unsupported.addAll(base.unsupportedSources()); checkpoint = base.checkpoint();
        }
        private Map<String, CanonicalRecord> map(SourceKind kind) {
            return switch (kind) { case JOB -> jobs; case BUILD -> builds; case QUEUE -> queue;
                case NODE -> nodes; case FINGERPRINT -> fingerprints; case PLUGIN -> plugins; };
        }
        private void replace(SourceKind kind, Collection<? extends CanonicalRecord> records) {
            Map<String, CanonicalRecord> target = map(kind); target.clear();
            for (CanonicalRecord record : records) target.put(record.key(), record);
        }
        private void clearErrors(SourceKind kind) { errors.removeIf(error -> error.source() == kind); }
        private long fence(SourceKind kind, String key) {
            String prefix = kind.name() + ":" + key + ":";
            return errors.stream().filter(error -> error.code().equals(DELETE_FENCE) && error.recordKey().equals(key)
                    && error.message().startsWith(prefix)).mapToLong(error -> Long.parseLong(error.message().substring(prefix.length())))
                    .max().orElse(-1);
        }
        private void putFence(SourceKind kind, String key, long sequence) {
            removeFence(kind, key); errors.add(new SourceError(kind, key, DELETE_FENCE, kind.name() + ":" + key + ":" + sequence));
        }
        private void removeFence(SourceKind kind, String key) {
            errors.removeIf(error -> error.source() == kind && error.recordKey().equals(key) && error.code().equals(DELETE_FENCE));
        }
        private boolean referencesBuild(String key) {
            return fingerprints.values().stream().map(FingerprintRecord.class::cast)
                    .anyMatch(fingerprint -> fingerprint.producerBuildKey().equals(key)
                            || fingerprint.consumerBuildKeys().contains(key));
        }
        @SuppressWarnings("unchecked")
        private Snapshot snapshot() {
            return new Snapshot((Map<String, JobRecord>) (Map<?, ?>) jobs, (Map<String, BuildRecord>) (Map<?, ?>) builds,
                    (Map<String, QueueRecord>) (Map<?, ?>) queue, (Map<String, NodeRecord>) (Map<?, ?>) nodes,
                    (Map<String, FingerprintRecord>) (Map<?, ?>) fingerprints,
                    (Map<String, PluginRecord>) (Map<?, ?>) plugins, errors, unsupported, checkpoint);
        }
    }
}