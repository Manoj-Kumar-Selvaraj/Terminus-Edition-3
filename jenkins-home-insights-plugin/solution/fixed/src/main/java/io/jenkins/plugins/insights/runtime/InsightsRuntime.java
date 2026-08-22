package io.jenkins.plugins.insights.runtime;

import io.jenkins.plugins.insights.analysis.AnalysisEngine;
import io.jenkins.plugins.insights.journal.EventJournal;
import io.jenkins.plugins.insights.journal.EventJournal.AppendResult;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;
import io.jenkins.plugins.insights.journal.JournalMaintenance;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.model.Domain.SourceKind;
import io.jenkins.plugins.insights.query.QueryService;
import io.jenkins.plugins.insights.query.QueryService.Principal;
import io.jenkins.plugins.insights.query.QueryService.Request;
import io.jenkins.plugins.insights.query.QueryService.Response;
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
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public final class InsightsRuntime implements Closeable {
    public enum Phase { STARTING, RECOVERING, READY, RECONCILING, STOPPING, STOPPED, FAILED }
    public record Health(Phase phase, boolean ready, boolean currentValid, long checkpoint, long journalTail,
                         long replayLag, int records, int sourceErrors, Set<SourceKind> unsupportedSources,
                         long droppedHints, List<String> diagnostics) {
        public Map<String, Object> toMap() { return Domain.ordered("phase", phase.name(), "ready", ready,
                "currentValid", currentValid, "checkpoint", checkpoint, "journalTail", journalTail,
                "replayLag", replayLag, "records", records, "sourceErrors", sourceErrors,
                "unsupportedSources", unsupportedSources.stream().map(Enum::name).sorted().toList(),
                "droppedHints", droppedHints, "diagnostics", diagnostics); }
    }

    private static final long OBSERVATION_TIME = 1_735_689_600_000L;
    private final Path home;
    private final AtomicBoolean stopping = new AtomicBoolean();
    private final AtomicReference<Phase> phase = new AtomicReference<>(Phase.STARTING);
    private final EventJournal journal;
    private final EventJournal.Ingress ingress;
    private final GenerationStore generations;
    private final ReconciliationEngine reconciler;
    private final AnalysisEngine analyzer = new AnalysisEngine();
    private final SnapshotAuditor auditor = new SnapshotAuditor();
    private final JournalMaintenance journalMaintenance = new JournalMaintenance();
    private final ReadinessEvaluator readinessEvaluator = new ReadinessEvaluator();
    private final RuntimeMetrics metrics = new RuntimeMetrics();
    private final QueryService queries = new QueryService(new QueryService.JenkinsStyleAccessPolicy());
    private volatile Snapshot snapshot = Snapshot.empty();
    private volatile AnalysisEngine.Analysis analysis = analyzer.analyze(snapshot, OBSERVATION_TIME);
    private volatile String generationId = "";
    private final List<String> diagnostics = new ArrayList<>();

    public InsightsRuntime(Path home, Path state) throws IOException {
        this.home = home.toAbsolutePath().normalize(); Path normalizedState = state.toAbsolutePath().normalize();
        journal = new EventJournal(normalizedState); ingress = new EventJournal.Ingress(1024);
        generations = new GenerationStore(normalizedState);
        reconciler = new ReconciliationEngine(HomeSources.standardAdapters(), stopping); recover();
    }

    public synchronized void recover() throws IOException {
        metrics.recoveryStarted(); phase.set(Phase.RECOVERING);
        try {
            GenerationStore.RecoverySelection selection = generations.recover();
            snapshot = selection.snapshot(); generationId = selection.generationId(); diagnostics.addAll(selection.diagnostics());
            EventJournal.Recovery recovery = EventJournal.recover(journal.path(), snapshot.checkpoint().appliedSequence());
            diagnostics.addAll(recovery.diagnostics());
            if (recovery.tornTail()) diagnostics.add("journal tail isolated");
            if (!recovery.events().isEmpty()) {
                boolean dirty = recovery.events().stream().anyMatch(event -> event.operation() == Domain.EventOperation.DIRTY);
                if (dirty) {
                    ReconciliationEngine.ReconcileResult full = reconciler.full(new HomeSources.ScanContext(home, recovery.lastGoodSequence(), 256));
                    if (full.cancelled()) throw new IOException("recovery reconciliation cancelled"); snapshot = full.snapshot();
                } else {
                    ReconciliationEngine.ReconcileResult reduced = reconciler.incremental(snapshot, recovery.events());
                    if (reduced.rejectedEvents() > 0 || reduced.cancelled()) throw new IOException("journal replay did not converge");
                    snapshot = reduced.snapshot();
                }
                analysis = analyzer.analyze(snapshot, OBSERVATION_TIME);
                GenerationStore.Published published = generations.publish(snapshot, analysis.toMap());
                snapshot = published.snapshot(); generationId = published.generationId();
            }
            analysis = analyzer.analyze(snapshot, OBSERVATION_TIME); metrics.recoveryCompleted(); phase.set(Phase.READY);
        } catch (IOException failure) {
            diagnostics.add("recovery deferred: " + failure.getMessage()); snapshot = Snapshot.empty(); generationId = ""; phase.set(Phase.STARTING);
        }
    }

    public synchronized GenerationStore.Published reconcileFull() throws IOException {
        requireRunning(); phase.set(Phase.RECONCILING);
        try {
            long sequence = Math.max(0, journal.nextSequence() - 1);
            ReconciliationEngine.ReconcileResult result = reconciler.full(new HomeSources.ScanContext(home, sequence, 256));
            if (result.cancelled() || stopping.get()) throw new IOException("reconciliation cancelled");
            AnalysisEngine.Analysis nextAnalysis = analyzer.analyze(result.snapshot(), OBSERVATION_TIME);
            if (stopping.get()) throw new IOException("publication fenced by shutdown");
            GenerationStore.Published published = generations.publish(result.snapshot(), nextAnalysis.toMap());
            snapshot = published.snapshot(); analysis = nextAnalysis; generationId = published.generationId();
            metrics.fullPublished(); phase.set(Phase.READY); return published;
        } catch (IOException | RuntimeException failure) { if (!stopping.get()) phase.set(Phase.FAILED); throw failure; }
    }

    public synchronized int drainEvents() throws IOException, InterruptedException {
        requireRunning(); Set<SourceKind> dirty = ingress.consumeDirtySources();
        if (!dirty.isEmpty()) {
            try { reconcileFull(); ingress.clearDropped(); return 0; }
            catch (IOException failure) { ingress.restoreDirtySources(dirty); throw failure; }
        }
        List<Hint> hints = ingress.drain(256, 1); if (hints.isEmpty()) return 0;
        List<Domain.Event> events = new ArrayList<>();
        for (Hint hint : hints) {
            AppendResult result = journal.append(hint.eventId(), hint.source(), hint.operation(), hint.recordKey(), hint.payload());
            if (result.status() == EventJournal.AppendStatus.CONFLICT) throw new IOException(result.message());
            if (result.status() == EventJournal.AppendStatus.CLOSED) throw new IOException(result.message());
            if (result.status() == EventJournal.AppendStatus.APPENDED) events.add(new Domain.Event(result.sequence(), hint.eventId(),
                    hint.source(), hint.operation(), hint.recordKey(), Domain.sha256(Json.write(hint.payload())), hint.payload()));
        }
        if (events.isEmpty()) return 0;
        ReconciliationEngine.ReconcileResult reduced = reconciler.incremental(snapshot, events);
        if (reduced.cancelled() || reduced.rejectedEvents() > 0) throw new IOException("event batch was not fully reduced");
        AnalysisEngine.Analysis nextAnalysis = analyzer.analyze(reduced.snapshot(), OBSERVATION_TIME);
        if (stopping.get()) throw new IOException("publication fenced by shutdown");
        GenerationStore.Published published = generations.publish(reduced.snapshot(), nextAnalysis.toMap());
        snapshot = published.snapshot(); analysis = nextAnalysis; generationId = published.generationId();
        metrics.incrementalPublished(reduced.appliedEvents()); return reduced.appliedEvents();
    }

    public boolean offer(Hint hint) {
        if (stopping.get()) return false;
        boolean accepted = ingress.offer(hint);
        if (!accepted) try {
            journal.append("dirty:" + hint.source().name().toLowerCase() + ":" + journal.nextSequence(), hint.source(),
                    Domain.EventOperation.DIRTY, hint.recordKey(), Map.of("source", hint.source().name()));
        } catch (IOException failure) { synchronized (diagnostics) { diagnostics.add("dirty obligation failed: " + failure.getMessage()); } }
        return accepted;
    }
    public Response query(Principal principal, Request request) {
        if (generationId.isBlank()) throw new IllegalStateException("no published generation");
        try (GenerationStore.Lease ignored = generations.lease(generationId, principal.name())) {
            Response response = queries.execute(generationId, snapshot, analysis, principal, request);
            metrics.queryCompleted(); return response;
        } catch (IOException failure) { throw new IllegalStateException("query lease failed", failure); }
    }
    public GenerationStore.RetentionResult compact(int retain) throws IOException { requireRunning(); return generations.compact(retain); }
    public List<String> generations() throws IOException { return generations.inventory(); }
    public Snapshot snapshot() { return snapshot; }

    public Health health() {
        boolean valid = false; List<String> messages; synchronized (diagnostics) { messages = new ArrayList<>(diagnostics); }
        GenerationStore.Verification verification = null;
        try { verification = generations.verifyCurrent(); valid = verification.valid(); messages.addAll(verification.errors()); }
        catch (IOException failure) { messages.add(failure.getMessage()); }
        long tail = Math.max(0, journal.nextSequence() - 1); long checkpoint = snapshot.checkpoint().appliedSequence();
        SnapshotAuditor.Audit audit = auditor.audit(snapshot); if (!audit.valid()) messages.add("canonical snapshot audit reports invalid state");
        JournalMaintenance.Inspection inspection = null;
        try { inspection = journalMaintenance.inspect(journal.path()); if (!inspection.healthy()) messages.add("event journal inspection reports degraded state"); }
        catch (IOException failure) { messages.add("journal inspection failed: " + failure.getMessage()); }
        ReadinessEvaluator.Evaluation evaluation = readinessEvaluator.evaluate(phase.get(), generationId, snapshot,
                verification, inspection, audit, ingress.droppedCount());
        messages.addAll(evaluation.diagnostics()); messages.add("runtime metrics: " + Json.write(metrics.snapshot().toMap()));
        return new Health(phase.get(), evaluation.ready(), valid, checkpoint, tail, Math.max(0, tail - checkpoint),
                snapshot.recordCount(), snapshot.errors().size(), snapshot.unsupportedSources(), ingress.droppedCount(), List.copyOf(messages));
    }
    private void requireRunning() { if (stopping.get()) throw new IllegalStateException("runtime is stopping"); }
    @Override public synchronized void close() throws IOException {
        if (!stopping.compareAndSet(false, true)) return;
        phase.set(Phase.STOPPING); ingress.stop(); journal.flush(); journal.close(); phase.set(Phase.STOPPED);
    }
}