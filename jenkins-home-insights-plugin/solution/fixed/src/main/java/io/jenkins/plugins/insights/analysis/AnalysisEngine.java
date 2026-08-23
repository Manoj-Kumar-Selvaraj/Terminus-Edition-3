package io.jenkins.plugins.insights.analysis;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.*;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

public final class AnalysisEngine {
    public record QueueAssessment(String queueKey, String taskKey, QueueBlockage blockage,
                                  int matchingNodes, int matchingExecutors, int availableExecutors,
                                  long ageMillis, Set<String> requestedLabels) {
        public Map<String, Object> toMap() { return Domain.ordered("queueKey", queueKey, "taskKey", taskKey,
                "blockage", blockage.name(), "matchingNodes", matchingNodes, "matchingExecutors", matchingExecutors,
                "availableExecutors", availableExecutors, "ageMillis", ageMillis, "requestedLabels", requestedLabels); }
    }
    public record QueueSummary(List<QueueAssessment> items, int demand, int capacity, int available,
                               double pressure, Map<QueueBlockage, Long> blockageCounts) {
        public Map<String, Object> toMap() {
            Map<String, Long> counts = new TreeMap<>(); blockageCounts.forEach((key, value) -> counts.put(key.name(), value));
                Object serializedPressure = Double.isFinite(pressure) ? pressure : "unbounded";
                return Domain.ordered("items", items.stream().map(QueueAssessment::toMap).toList(), "demand", demand,
                    "capacity", capacity, "available", available, "pressure", serializedPressure, "blockageCounts", counts);
        }
    }
    public record BuildHealth(String jobKey, int total, int success, int unstable, int failed, int aborted,
                              int running, int missing, int malformed, long latestStart,
                              long medianDurationMillis, double successRate) {
        public Map<String, Object> toMap() { return Domain.ordered("jobKey", jobKey, "total", total, "success", success,
                "unstable", unstable, "failed", failed, "aborted", aborted, "running", running, "missing", missing,
                "malformed", malformed, "latestStart", latestStart, "medianDurationMillis", medianDurationMillis,
                "successRate", successRate); }
    }
    public record LineageEdge(String fingerprintKey, String producerBuildKey, String consumerBuildKey,
                              String producerJobKey, String consumerJobKey, boolean producerMissing,
                              boolean consumerMissing) {
        public Map<String, Object> toMap() { return Domain.ordered("fingerprintKey", fingerprintKey,
                "producerBuildKey", producerBuildKey, "consumerBuildKey", consumerBuildKey,
                "producerJobKey", producerJobKey, "consumerJobKey", consumerJobKey,
                "producerMissing", producerMissing, "consumerMissing", consumerMissing); }
    }
    public record LineageSummary(List<LineageEdge> edges, int fingerprints, int missingProducers,
                                 int missingConsumers, Map<String, Integer> downstreamCounts,
                                 List<List<String>> cycles) {
        public Map<String, Object> toMap() { return Domain.ordered("edges", edges.stream().map(LineageEdge::toMap).toList(),
                "fingerprints", fingerprints, "missingProducers", missingProducers, "missingConsumers", missingConsumers,
                "downstreamCounts", downstreamCounts, "cycles", cycles); }
    }
    public record PluginAssessment(String key, String shortName, String version, PluginState state,
                                   boolean bundled, Set<String> missingDependencies) {
        public Map<String, Object> toMap() { return Domain.ordered("key", key, "shortName", shortName, "version", version,
                "state", state.name(), "bundled", bundled, "missingDependencies", missingDependencies); }
    }
    public record PluginSummary(List<PluginAssessment> plugins, Map<PluginState, Long> stateCounts,
                                boolean restartRequired, int dependencyFailures) {
        public Map<String, Object> toMap() {
            Map<String, Long> counts = new TreeMap<>(); stateCounts.forEach((key, value) -> counts.put(key.name(), value));
            return Domain.ordered("plugins", plugins.stream().map(PluginAssessment::toMap).toList(), "stateCounts", counts,
                    "restartRequired", restartRequired, "dependencyFailures", dependencyFailures);
        }
    }
    public record Analysis(QueueSummary queue, List<BuildHealth> buildHealth, LineageSummary lineage,
                           PluginSummary plugins) {
        public Map<String, Object> toMap() { return Domain.ordered("queue", queue.toMap(),
                "buildHealth", buildHealth.stream().map(BuildHealth::toMap).toList(),
                "lineage", lineage.toMap(), "plugins", plugins.toMap()); }
    }

    public Analysis analyze(Snapshot snapshot, long observationMillis) {
        return new Analysis(analyzeQueue(snapshot, observationMillis), analyzeBuilds(snapshot),
                analyzeLineage(snapshot), analyzePlugins(snapshot));
    }

    public QueueSummary analyzeQueue(Snapshot snapshot, long observationMillis) {
        List<QueueAssessment> assessments = new ArrayList<>(); Map<QueueBlockage, Long> counts = new EnumMap<>(QueueBlockage.class);
        int capacity = snapshot.nodes().values().stream().filter(node -> node.online() && node.acceptingTasks())
                .mapToInt(NodeRecord::executors).sum();
        int available = snapshot.nodes().values().stream().mapToInt(NodeRecord::availableExecutors).sum();
        int demand = 0;
        for (QueueRecord item : snapshot.queue().values()) {
            QueueBlockage blockage; List<NodeRecord> matching;
            if (item.cancelled()) { blockage = QueueBlockage.CANCELLED; matching = List.of(); }
            else {
                demand++;
                matching = snapshot.nodes().values().stream().filter(node -> eligible(node, item.labels())).toList();
                boolean exclusiveOnly = item.labels().isEmpty() && snapshot.nodes().values().stream()
                        .anyMatch(node -> node.mode() == NodeMode.EXCLUSIVE);
                if (matching.isEmpty()) blockage = exclusiveOnly ? QueueBlockage.EXCLUSIVE_REJECTED : QueueBlockage.LABEL_MISMATCH;
                else if (matching.stream().noneMatch(NodeRecord::online)) blockage = QueueBlockage.OFFLINE;
                else if (matching.stream().noneMatch(node -> node.online() && node.acceptingTasks() && node.executors() > 0)) blockage = QueueBlockage.NO_EXECUTOR;
                else if (matching.stream().mapToInt(NodeRecord::availableExecutors).sum() == 0) blockage = QueueBlockage.NO_EXECUTOR;
                else blockage = QueueBlockage.RUNNABLE;
            }
            int configured = matching.stream().filter(node -> node.online() && node.acceptingTasks()).mapToInt(NodeRecord::executors).sum();
            int free = matching.stream().mapToInt(NodeRecord::availableExecutors).sum();
            QueueAssessment assessment = new QueueAssessment(item.key(), item.taskKey(), blockage, matching.size(), configured,
                    free, Math.max(0, observationMillis - item.enqueuedMillis()), item.labels());
            assessments.add(assessment); counts.merge(blockage, 1L, Long::sum);
        }
        assessments.sort(Comparator.comparing(QueueAssessment::blockage).thenComparing(QueueAssessment::queueKey));
        double pressure = capacity == 0 ? demand == 0 ? 0.0 : Double.POSITIVE_INFINITY : (double) demand / capacity;
        return new QueueSummary(List.copyOf(assessments), demand, capacity, available, pressure, Map.copyOf(counts));
    }

    private boolean eligible(NodeRecord node, Set<String> labels) {
        if (labels.isEmpty()) return node.mode() == NodeMode.NORMAL;
        return node.labels().containsAll(labels);
    }

    public List<BuildHealth> analyzeBuilds(Snapshot snapshot) {
        Map<String, List<BuildRecord>> byJob = new HashMap<>();
        snapshot.builds().values().forEach(build -> byJob.computeIfAbsent(build.jobKey(), ignored -> new ArrayList<>()).add(build));
        List<BuildHealth> result = new ArrayList<>();
        for (Map.Entry<String, List<BuildRecord>> entry : byJob.entrySet()) {
            int success = 0, unstable = 0, failed = 0, aborted = 0, running = 0, missing = 0, malformed = 0, total = 0;
            long latest = 0; List<Long> durations = new ArrayList<>();
            for (BuildRecord build : entry.getValue()) {
                if (build.state() == RecordState.DELETED) continue;
                total++;
                if (build.state() == RecordState.MALFORMED || build.startedMillis() < 0 || build.durationMillis() < 0) malformed++;
                else if (build.state() == RecordState.RUNNING || build.result() == BuildResult.RUNNING) running++;
                else switch (build.result()) {
                    case SUCCESS -> success++; case UNSTABLE -> unstable++; case FAILURE -> failed++;
                    case ABORTED, NOT_BUILT -> aborted++; case MISSING -> missing++; case MALFORMED -> malformed++;
                    case RUNNING -> running++;
                }
                if (build.startedMillis() >= 0) latest = Math.max(latest, build.startedMillis());
                if (build.durationMillis() > 0 && build.state() != RecordState.MALFORMED) durations.add(build.durationMillis());
            }
            durations.sort(Long::compareTo); long median = durations.isEmpty() ? 0 : durations.get((durations.size() - 1) / 2);
            int completed = success + unstable + failed + aborted;
            result.add(new BuildHealth(entry.getKey(), total, success, unstable, failed, aborted, running, missing,
                    malformed, latest, median, completed == 0 ? 0.0 : (double) success / completed));
        }
        result.sort(Comparator.comparing(BuildHealth::jobKey)); return List.copyOf(result);
    }

    public LineageSummary analyzeLineage(Snapshot snapshot) {
        List<LineageEdge> edges = new ArrayList<>(); int missingProducers = 0; int missingConsumers = 0;
        Map<String, Set<String>> graph = new HashMap<>(); Map<String, Set<String>> downstream = new TreeMap<>();
        for (FingerprintRecord fingerprint : snapshot.fingerprints().values()) {
            BuildRecord producer = snapshot.builds().get(fingerprint.producerBuildKey());
            boolean producerMissing = producer == null || producer.state() == RecordState.DELETED || fingerprint.producerMissing();
            if (producerMissing) missingProducers++;
            for (String consumerKey : fingerprint.consumerBuildKeys()) {
                BuildRecord consumer = snapshot.builds().get(consumerKey);
                boolean consumerMissing = consumer == null || consumer.state() == RecordState.DELETED;
                if (consumerMissing) missingConsumers++;
                String producerJob = producer == null ? "" : producer.jobKey(); String consumerJob = consumer == null ? "" : consumer.jobKey();
                edges.add(new LineageEdge(fingerprint.key(), fingerprint.producerBuildKey(), consumerKey,
                        producerJob, consumerJob, producerMissing, consumerMissing));
                if (!producerJob.isBlank() && !consumerJob.isBlank()) {
                    graph.computeIfAbsent(producerJob, ignored -> new LinkedHashSet<>()).add(consumerJob);
                    downstream.computeIfAbsent(producerJob, ignored -> new LinkedHashSet<>()).add(consumerJob);
                }
            }
        }
        edges.sort(Comparator.comparing(LineageEdge::fingerprintKey).thenComparing(LineageEdge::consumerBuildKey));
        Map<String, Integer> counts = new TreeMap<>(); downstream.forEach((key, value) -> counts.put(key, value.size()));
        return new LineageSummary(List.copyOf(edges), snapshot.fingerprints().size(), missingProducers,
                missingConsumers, Map.copyOf(counts), cycles(graph));
    }

    private List<List<String>> cycles(Map<String, Set<String>> graph) {
        List<List<String>> result = new ArrayList<>(); Set<String> complete = new HashSet<>(); Set<String> active = new HashSet<>();
        for (String node : new TreeMap<>(graph).keySet()) visit(node, graph, complete, active, new ArrayDeque<>(), result);
        result.sort(Comparator.comparing(path -> String.join("\u0000", path))); return List.copyOf(result);
    }
    private void visit(String node, Map<String, Set<String>> graph, Set<String> complete, Set<String> active,
                       Deque<String> path, List<List<String>> cycles) {
        if (complete.contains(node)) return;
        if (active.contains(node)) {
            List<String> cycle = new ArrayList<>(); boolean capture = false;
            for (String item : path) { if (item.equals(node)) capture = true; if (capture) cycle.add(item); }
            cycle.add(node); cycles.add(List.copyOf(cycle)); return;
        }
        active.add(node); path.addLast(node);
        for (String target : graph.getOrDefault(node, Set.of()).stream().sorted().toList()) visit(target, graph, complete, active, path, cycles);
        path.removeLast(); active.remove(node); complete.add(node);
    }

    public PluginSummary analyzePlugins(Snapshot snapshot) {
        List<PluginAssessment> assessments = new ArrayList<>(); Map<PluginState, Long> counts = new EnumMap<>(PluginState.class);
        for (PluginRecord plugin : snapshot.plugins().values()) {
            PluginState state;
            if (!plugin.enabled()) state = PluginState.DISABLED;
            else if (!plugin.missingDependencies().isEmpty()) state = PluginState.DEPENDENCY_MISSING;
            else if (!plugin.compatible()) state = PluginState.INCOMPATIBLE;
            else if (!plugin.active()) state = PluginState.FAILED;
            else if (plugin.restartPending()) state = PluginState.RESTART_PENDING;
            else if (plugin.bundled()) state = PluginState.BUNDLED;
            else state = PluginState.ENABLED;
            PluginAssessment assessment = new PluginAssessment(plugin.key(), plugin.shortName(), plugin.version(), state,
                    plugin.bundled(), plugin.missingDependencies());
            assessments.add(assessment); counts.merge(state, 1L, Long::sum);
        }
        assessments.sort(Comparator.comparing(PluginAssessment::shortName).thenComparing(PluginAssessment::key));
        boolean restart = snapshot.plugins().values().stream().anyMatch(PluginRecord::restartPending);
        int missing = snapshot.plugins().values().stream().mapToInt(plugin -> plugin.missingDependencies().size()).sum();
        return new PluginSummary(List.copyOf(assessments), Map.copyOf(counts), restart, missing);
    }
}