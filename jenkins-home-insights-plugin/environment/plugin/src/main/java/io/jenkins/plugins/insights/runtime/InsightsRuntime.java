package io.jenkins.plugins.insights.runtime;

import io.jenkins.plugins.insights.analysis.AnalysisEngine;
import io.jenkins.plugins.insights.journal.EventJournal;
import io.jenkins.plugins.insights.journal.EventJournal.AppendResult;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;
import io.jenkins.plugins.insights.journal.JournalMaintenance;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.model.Domain.SourceKind;
import io.jenkins.plugins.insights.query.QueryService;
import io.jenkins.plugins.insights.query.QueryService.Principal;
import io.jenkins.plugins.insights.query.QueryService.Request;
import io.jenkins.plugins.insights.query.QueryService.Response;
import io.jenkins.plugins.insights.reconcile.EventBatchPlanner;
import io.jenkins.plugins.insights.reconcile.ReconciliationEngine;
import io.jenkins.plugins.insights.source.HomeSources;
import io.jenkins.plugins.insights.storage.GenerationStore;
import io.jenkins.plugins.insights.storage.SnapshotAuditor;

import java.io.Closeable;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Lifecycle owner shared by Jenkins hooks and the standalone operator. */
public final class InsightsRuntime implements Closeable {
    public enum Phase { STARTING, RECOVERING, READY, RECONCILING, STOPPING, STOPPED, FAILED }
    public record Health(Phase phase, boolean ready, boolean currentValid, long checkpoint,
                         long journalTail, long replayLag, int records, int sourceErrors,
                         Set<SourceKind> unsupportedSources, long droppedHints, List<String> diagnostics) {
        public Map<String, Object> toMap() {
            return Domain.ordered("phase", phase.name(), "ready", ready, "currentValid", currentValid,
                    "checkpoint", checkpoint, "journalTail", journalTail, "replayLag", replayLag,
                    "records", records, "sourceErrors", sourceErrors,
                    "unsupportedSources", unsupportedSources.stream().map(Enum::name).toList(),
                    "droppedHints", droppedHints, "diagnostics", diagnostics);
        }
    }

    private final Path home;
    private final Path state;
    private final AtomicBoolean stopping = new AtomicBoolean();
    private final AtomicReference<Phase> phase = new AtomicReference<>(Phase.STARTING);
    private final EventJournal journal;
    private final EventJournal.Ingress ingress;
    private final GenerationStore generations;
    private final ReconciliationEngine reconciler;
    private final AnalysisEngine analyzer = new AnalysisEngine();
    private final EventBatchPlanner batchPlanner = new EventBatchPlanner();
    private final SnapshotAuditor auditor = new SnapshotAuditor();
    private final JournalMaintenance journalMaintenance = new JournalMaintenance();
    private final ReadinessEvaluator readinessEvaluator = new ReadinessEvaluator();
    private final RuntimeMetrics metrics = new RuntimeMetrics();
    private final QueryService queries = new QueryService(new QueryService.JenkinsStyleAccessPolicy());
    private volatile Snapshot snapshot = Snapshot.empty();
    private volatile AnalysisEngine.Analysis analysis = analyzer.analyze(snapshot, 1_735_689_600_000L);
    private volatile String generationId = "";
    private final List<String> diagnostics = new ArrayList<>();

    public InsightsRuntime(Path home, Path state) throws IOException {
        this.home = home.toAbsolutePath().normalize(); this.state = state.toAbsolutePath().normalize();
        this.journal = new EventJournal(this.state); this.ingress = new EventJournal.Ingress(1024);
        this.generations = new GenerationStore(this.state);
        this.reconciler = new ReconciliationEngine(HomeSources.standardAdapters(), stopping);
        recover();
    }

    public synchronized void recover() throws IOException {
        metrics.recoveryStarted();
        phase.set(Phase.RECOVERING);
        try {
            GenerationStore.RecoverySelection selection = generations.recover();
            snapshot = selection.snapshot(); generationId = selection.generationId(); diagnostics.addAll(selection.diagnostics());
            EventJournal.Recovery events = EventJournal.recover(journal.path(), snapshot.checkpoint().appliedSequence());
            diagnostics.addAll(events.diagnostics());
            if (!events.events().isEmpty()) snapshot = reconciler.incremental(snapshot, events.events()).snapshot();
            analysis = analyzer.analyze(snapshot, 1_735_689_600_000L); metrics.recoveryCompleted(); phase.set(Phase.READY);
        } catch (IOException missing) {
            diagnostics.add("recovery deferred: " + missing.getMessage()); snapshot = Snapshot.empty(); phase.set(Phase.STARTING);
        }
    }

    public synchronized GenerationStore.Published reconcileFull() throws IOException {
        requireRunning(); phase.set(Phase.RECONCILING);
        long sequence = Math.max(0, journal.nextSequence() - 1);
        ReconciliationEngine.ReconcileResult result = reconciler.full(new HomeSources.ScanContext(home, sequence, 256));
        if (result.cancelled()) throw new IOException("reconciliation cancelled");
        snapshot = result.snapshot(); analysis = analyzer.analyze(snapshot, 1_735_689_600_000L);
        GenerationStore.Published published = generations.publish(snapshot, analysis.toMap()); generationId = published.generationId();
        metrics.fullPublished();
        phase.set(Phase.READY); return published;
    }

    public synchronized int drainEvents() throws IOException, InterruptedException {
        requireRunning(); List<Hint> hints = ingress.drain(256, 1); if (hints.isEmpty()) return 0;
        List<Domain.Event> events = new ArrayList<>();
        for (Hint hint : hints) {
            AppendResult result = journal.append(hint.eventId(), hint.source(), hint.operation(), hint.recordKey(), hint.payload());
            if (result.status() == EventJournal.AppendStatus.APPENDED) {
                events.add(new Domain.Event(result.sequence(), hint.eventId(), hint.source(), hint.operation(),
                        hint.recordKey(), Domain.sha256(io.jenkins.plugins.insights.json.Json.write(hint.payload())), hint.payload()));
            }
        }
        EventBatchPlanner.Batch batch = batchPlanner.plan(events, snapshot.checkpoint().appliedSequence(), 256);
        ReconciliationEngine.ReconcileResult reduced = reconciler.incremental(snapshot, batch.events());
        snapshot = reduced.snapshot(); analysis = analyzer.analyze(snapshot, 1_735_689_600_000L);
        GenerationStore.Published published = generations.publish(snapshot, analysis.toMap()); generationId = published.generationId();
        metrics.incrementalPublished(reduced.appliedEvents());
        return reduced.appliedEvents();
    }

    public boolean offer(Hint hint) { return ingress.offer(hint); }
    public Response query(Principal principal, Request request) {
        Response response = queries.execute(generationId, snapshot, analysis, principal, request);
        metrics.queryCompleted(); return response;
    }
    public GenerationStore.RetentionResult compact(int retain) throws IOException { requireRunning(); return generations.compact(retain); }
    public List<String> generations() throws IOException { return generations.inventory(); }
    public Snapshot snapshot() { return snapshot; }

    public Health health() {
        boolean valid = false; List<String> messages = new ArrayList<>(diagnostics);
        GenerationStore.Verification verification = null;
        try { verification = generations.verifyCurrent(); valid = verification.valid(); messages.addAll(verification.errors()); }
        catch (IOException failure) { messages.add(failure.getMessage()); }
        long tail = Math.max(0, journal.nextSequence() - 1); long checkpoint = snapshot.checkpoint().appliedSequence();
        SnapshotAuditor.Audit audit = auditor.audit(snapshot);
        if (!audit.valid()) messages.add("canonical snapshot audit reports invalid state");
        JournalMaintenance.Inspection inspection = null;
        try {
            inspection = journalMaintenance.inspect(journal.path());
            if (!inspection.healthy()) messages.add("event journal inspection reports degraded state");
        } catch (IOException failure) { messages.add("journal inspection failed: " + failure.getMessage()); }
        ReadinessEvaluator.Evaluation evaluation = readinessEvaluator.evaluate(phase.get(), generationId, snapshot,
                verification, inspection, audit, ingress.droppedCount());
        messages.addAll(evaluation.diagnostics());
        messages.add("runtime metrics: " + io.jenkins.plugins.insights.json.Json.write(metrics.snapshot().toMap()));
        boolean ready = evaluation.ready();
        return new Health(phase.get(), ready, valid, checkpoint, tail, Math.max(0, tail - checkpoint), snapshot.recordCount(),
                snapshot.errors().size(), snapshot.unsupportedSources(), ingress.droppedCount(), List.copyOf(messages));
    }

    private void requireRunning() { if (stopping.get()) throw new IllegalStateException("runtime is stopping"); }

    @Override public synchronized void close() throws IOException {
        if (!stopping.compareAndSet(false, true)) return;
        phase.set(Phase.STOPPING); ingress.stop(); journal.close(); phase.set(Phase.STOPPED);
    }
}
