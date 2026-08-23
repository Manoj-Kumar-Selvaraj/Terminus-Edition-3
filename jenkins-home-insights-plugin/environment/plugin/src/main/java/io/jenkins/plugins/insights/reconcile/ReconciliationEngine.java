package io.jenkins.plugins.insights.reconcile;

import io.jenkins.plugins.insights.journal.EventJournal;
import io.jenkins.plugins.insights.model.Domain.*;
import io.jenkins.plugins.insights.source.HomeSources.ScanContext;
import io.jenkins.plugins.insights.source.HomeSources.ScanResult;
import io.jenkins.plugins.insights.source.HomeSources.SourceAdapter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

/** Coordinates bounded source scans and incremental journal reduction. */
public final class ReconciliationEngine {
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
            state.errors.addAll(result.errors()); if (!result.supported()) state.unsupported.add(result.source());
            completed.add(result.source());
        }
        state.checkpoint = new Checkpoint(context.sequence(), "", "");
        return finish(state, scanned, 0, 0, false, completed);
    }

    public ReconcileResult incremental(Snapshot base, Collection<Event> events) {
        MutableState state = new MutableState(base); Set<SourceKind> touched = EnumSet.noneOf(SourceKind.class);
        int applied = 0; int rejected = 0; long checkpoint = base.checkpoint().appliedSequence();
        Map<String, String> represented = new HashMap<>();
        for (Event event : events) {
            if (stopping.get()) return finish(state, 0, applied, rejected, true, touched);
            String previousHash = represented.putIfAbsent(event.eventId(), event.payloadHash());
            if (previousHash != null) { if (!previousHash.equals(event.payloadHash())) rejected++; continue; }
            try {
                apply(state, event); applied++; touched.add(event.source());
            } catch (RuntimeException invalid) {
                rejected++; state.errors.add(new SourceError(event.source(), event.recordKey(), "EVENT_REJECTED", invalid.getMessage()));
            }
            checkpoint = Math.max(checkpoint, event.sequence());
        }
        state.checkpoint = new Checkpoint(checkpoint, base.checkpoint().generationId(), base.checkpoint().digest());
        return finish(state, 0, applied, rejected, false, touched);
    }

    private void apply(MutableState state, Event event) {
        Map<String, CanonicalRecord> target = state.map(event.source());
        if (event.operation() == EventOperation.DELETE) { target.remove(event.recordKey()); return; }
        if (event.operation() == EventOperation.DIRTY) { state.unsupported.remove(event.source()); return; }
        CanonicalRecord record = RecordCodec.decode(event.source(), event.payload(), event.sequence());
        target.put(event.recordKey(), record);
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

        @SuppressWarnings("unchecked")
        private Snapshot snapshot() {
            return new Snapshot((Map<String, JobRecord>) (Map<?, ?>) jobs, (Map<String, BuildRecord>) (Map<?, ?>) builds,
                    (Map<String, QueueRecord>) (Map<?, ?>) queue, (Map<String, NodeRecord>) (Map<?, ?>) nodes,
                    (Map<String, FingerprintRecord>) (Map<?, ?>) fingerprints,
                    (Map<String, PluginRecord>) (Map<?, ?>) plugins, errors, unsupported, checkpoint);
        }
    }
}