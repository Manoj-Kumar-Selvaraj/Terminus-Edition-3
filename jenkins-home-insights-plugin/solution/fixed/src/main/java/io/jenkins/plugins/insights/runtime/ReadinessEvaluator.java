package io.jenkins.plugins.insights.runtime;

import io.jenkins.plugins.insights.journal.JournalMaintenance;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.storage.GenerationStore;
import io.jenkins.plugins.insights.storage.SnapshotAuditor;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ReadinessEvaluator {
    public enum Level { OK, DEGRADED, FAILED, UNKNOWN }
    public record Component(String name, Level level, String message, Map<String, Object> details) {
        public Map<String, Object> toMap() { return Domain.ordered("name", name, "level", level.name(), "message", message, "details", details); }
    }
    public record Evaluation(boolean ready, Level level, List<Component> components, List<String> diagnostics) {
        public Map<String, Object> toMap() { return Domain.ordered("ready", ready, "level", level.name(),
                "components", components.stream().map(Component::toMap).toList(), "diagnostics", diagnostics); }
    }

    public Evaluation evaluate(InsightsRuntime.Phase phase, String generationId, Snapshot snapshot,
                               GenerationStore.Verification generation, JournalMaintenance.Inspection journal,
                               SnapshotAuditor.Audit audit, long droppedHints) {
        List<Component> components = new ArrayList<>(); List<String> diagnostics = new ArrayList<>();
        components.add(lifecycle(phase)); components.add(generation(generationId, generation));
        components.add(journal(snapshot, journal)); components.add(snapshot(snapshot, audit));
        components.add(sources(snapshot)); components.add(ingress(droppedHints));
        for (Component component : components) if (component.level() != Level.OK) diagnostics.add(component.name() + ": " + component.message());
        Level level = components.stream().map(Component::level).max(java.util.Comparator.comparingInt(this::rank)).orElse(Level.UNKNOWN);
        boolean ready = phase == InsightsRuntime.Phase.READY && !generationId.isBlank()
                && generation != null && generation.valid() && journal != null && journal.healthy()
                && journal.lastSequence() <= snapshot.checkpoint().appliedSequence()
                && audit != null && audit.valid() && snapshot.unsupportedSources().isEmpty() && droppedHints == 0;
        return new Evaluation(ready, level, List.copyOf(components), List.copyOf(diagnostics));
    }
    private Component lifecycle(InsightsRuntime.Phase phase) {
        Level level = switch (phase) { case READY -> Level.OK; case STARTING, RECOVERING, RECONCILING -> Level.DEGRADED;
            case STOPPING, STOPPED, FAILED -> Level.FAILED; };
        return component("lifecycle", level, phase.name().toLowerCase(), "phase", phase.name());
    }
    private Component generation(String generationId, GenerationStore.Verification verification) {
        if (generationId.isBlank()) return component("generation", Level.UNKNOWN, "no published generation", "generationId", "");
        if (verification == null) return component("generation", Level.UNKNOWN, "verification unavailable", "generationId", generationId);
        Level level = verification.valid() ? Level.OK : Level.FAILED;
        return new Component("generation", level, verification.valid() ? "generation verified" : "generation invalid",
                Domain.ordered("generationId", generationId, "errors", verification.errors()));
    }
    private Component journal(Snapshot snapshot, JournalMaintenance.Inspection journal) {
        if (journal == null) return component("journal", Level.UNKNOWN, "inspection unavailable", "checkpoint", snapshot.checkpoint().appliedSequence());
        long lag = Math.max(0, journal.lastSequence() - snapshot.checkpoint().appliedSequence());
        Level level = journal.healthy() && lag == 0 ? Level.OK : journal.tornTail() ? Level.FAILED : Level.DEGRADED;
        return new Component("journal", level, level == Level.OK ? "checkpoint current" : "journal requires attention",
                Domain.ordered("firstSequence", journal.firstSequence(), "lastSequence", journal.lastSequence(),
                        "checkpoint", snapshot.checkpoint().appliedSequence(), "lag", lag,
                        "duplicateIds", journal.duplicateIds(), "sequenceGaps", journal.sequenceGaps(), "tornTail", journal.tornTail()));
    }
    private Component snapshot(Snapshot snapshot, SnapshotAuditor.Audit audit) {
        if (audit == null) return component("snapshot", Level.UNKNOWN, "audit unavailable", "records", snapshot.recordCount());
        Level level = audit.valid() ? audit.findings().isEmpty() ? Level.OK : Level.DEGRADED : Level.FAILED;
        return new Component("snapshot", level, audit.valid() ? "canonical state readable" : "canonical state invalid",
                Domain.ordered("records", audit.records(), "findings", audit.findings().size(), "digest", audit.canonicalDigest()));
    }
    private Component sources(Snapshot snapshot) {
        Level level = snapshot.unsupportedSources().isEmpty() ? Level.OK : Level.DEGRADED; Map<String, Integer> counts = new LinkedHashMap<>();
        counts.put("jobs", snapshot.jobs().size()); counts.put("builds", snapshot.builds().size()); counts.put("queue", snapshot.queue().size());
        counts.put("nodes", snapshot.nodes().size()); counts.put("fingerprints", snapshot.fingerprints().size()); counts.put("plugins", snapshot.plugins().size());
        return new Component("sources", level, level == Level.OK ? "all source capabilities available" : "source capability unavailable",
                Domain.ordered("counts", counts, "unsupported", snapshot.unsupportedSources().stream().map(Enum::name).sorted().toList(),
                        "errors", snapshot.errors().size()));
    }
    private Component ingress(long droppedHints) { return component("ingress", droppedHints == 0 ? Level.OK : Level.DEGRADED,
            droppedHints == 0 ? "no dropped hints" : "listener hints were dropped", "droppedHints", droppedHints); }
    private Component component(String name, Level level, String message, String key, Object value) {
        return new Component(name, level, message, Map.of(key, value));
    }
    private int rank(Level level) { return switch (level) { case OK -> 0; case UNKNOWN -> 1; case DEGRADED -> 2; case FAILED -> 3; }; }
}