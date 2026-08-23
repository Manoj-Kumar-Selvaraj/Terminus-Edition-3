package io.jenkins.plugins.insights.analysis;

import io.jenkins.plugins.insights.model.Domain.*;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.Deque;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;

/** Pure observational analysis over one immutable canonical snapshot. */
public final class AnalysisEngine {
    public record QueueAssessment(String queueKey, String taskKey, QueueBlockage blockage,
                                  int matchingNodes, int matchingExecutors, int availableExecutors,
                                  long ageMillis, Set<String> requestedLabels) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("queueKey", queueKey, "taskKey", taskKey,
                    "blockage", blockage.name(), "matchingNodes", matchingNodes,
                    "matchingExecutors", matchingExecutors, "availableExecutors", availableExecutors,
                    "ageMillis", ageMillis, "requestedLabels", requestedLabels);
        }
    }
    public record QueueSummary(List<QueueAssessment> items, int demand, int capacity, int available,
                               double pressure, Map<QueueBlockage, Long> blockageCounts) {
        public Map<String, Object> toMap() {
            Map<String, Long> counts = new TreeMap<>(); blockageCounts.forEach((key, value) -> counts.put(key.name(), value));
            return io.jenkins.plugins.insights.model.Domain.ordered("items", items.stream().map(QueueAssessment::toMap).toList(),
                    "demand", demand, "capacity", capacity, "available", available, "pressure", pressure,
                    "blockageCounts", counts);
        }
    }
    public record BuildHealth(String jobKey, int total, int success, int unstable, int failed,
                              int aborted, int running, int missing, int malformed,
                              long latestStart, long medianDurationMillis, double successRate) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("jobKey", jobKey, "total", total,
                    "success", success, "unstable", unstable, "failed", failed, "aborted", aborted,
                    "running", running, "missing", missing, "malformed", malformed,
                    "latestStart", latestStart, "medianDurationMillis", medianDurationMillis,
                    "successRate", successRate);
        }
    }
    public record LineageEdge(String fingerprintKey, String producerBuildKey, String consumerBuildKey,
                              String producerJobKey, String consumerJobKey, boolean producerMissing,
                              boolean consumerMissing) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("fingerprintKey", fingerprintKey,
                    "producerBuildKey", producerBuildKey, "consumerBuildKey", consumerBuildKey,
                    "producerJobKey", producerJobKey, "consumerJobKey", consumerJobKey,
                    "producerMissing", producerMissing, "consumerMissing", consumerMissing);
        }
    }
    public record LineageSummary(List<LineageEdge> edges, int fingerprints, int missingProducers,
                                 int missingConsumers, Map<String, Integer> downstreamCounts,
                                 List<List<String>> cycles) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("edges", edges.stream().map(LineageEdge::toMap).toList(),
                    "fingerprints", fingerprints, "missingProducers", missingProducers,
                    "missingConsumers", missingConsumers, "downstreamCounts", downstreamCounts, "cycles", cycles);
        }
    }
    public record PluginAssessment(String key, String shortName, String version, PluginState state,
                                   boolean bundled, Set<String> missingDependencies) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("key", key, "shortName", shortName,
                    "version", version, "state", state.name(), "bundled", bundled,
                    "missingDependencies", missingDependencies);
        }
    }
    public record PluginSummary(List<PluginAssessment> plugins, Map<PluginState, Long> stateCounts,
                                boolean restartRequired, int dependencyFailures) {
        public Map<String, Object> toMap() {
            Map<String, Long> counts = new TreeMap<>(); stateCounts.forEach((key, value) -> counts.put(key.name(), value));
            return io.jenkins.plugins.insights.model.Domain.ordered("plugins", plugins.stream().map(PluginAssessment::toMap).toList(),
                    "stateCounts", counts, "restartRequired", restartRequired, "dependencyFailures", dependencyFailures);
        }
    }
    public record Analysis(QueueSummary queue, List<BuildHealth> buildHealth, LineageSummary lineage,
                           PluginSummary plugins) {
        public Map<String, Object> toMap() {
            return io.jenkins.plugins.insights.model.Domain.ordered("queue", queue.toMap(),
                    "buildHealth", buildHealth.stream().map(BuildHealth::toMap).toList(),
                    "lineage", lineage.toMap(), "plugins", plugins.toMap());
        }
    }

    public Analysis analyze(Snapshot snapshot, long observationMillis) {
        return new Analysis(analyzeQueue(snapshot, observationMillis), analyzeBuilds(snapshot),
                analyzeLineage(snapshot), analyzePlugins(snapshot));
    }

    public QueueSummary analyzeQueue(Snapshot snapshot, long observationMillis) {
        List<QueueAssessment> assessments = new ArrayList<>();
        Map<QueueBlockage, Long> counts = new EnumMap<>(QueueBlockage.class);
        int capacity = snapshot.nodes().values().stream().filter(NodeRecord::online).mapToInt(NodeRecord::executors).sum();
        int available = snapshot.nodes().values().stream().mapToInt(NodeRecord::availableExecutors).sum();
        for (QueueRecord item : snapshot.queue().values()) {
            if (item.cancelled()) continue;
            List<NodeRecord> matching = snapshot.nodes().values().stream()
                    .filter(node -> node.labels().containsAll(item.labels())).toList();
            int matchingExecutors = matching.stream().mapToInt(NodeRecord::executors).sum();
            int matchingAvailable = matching.stream().mapToInt(NodeRecord::availableExecutors).sum();
            QueueBlockage blockage;
            if (matching.isEmpty()) blockage = QueueBlockage.LABEL_MISMATCH;
            else if (matching.stream().noneMatch(NodeRecord::online)) blockage = QueueBlockage.OFFLINE;
            else if (matchingAvailable == 0) blockage = QueueBlockage.NO_EXECUTOR;
            else blockage = QueueBlockage.RUNNABLE;
            QueueAssessment assessment = new QueueAssessment(item.key(), item.taskKey(), blockage,
                    matching.size(), matchingExecutors, matchingAvailable,
                    Math.max(0, observationMillis - item.enqueuedMillis()), item.labels());
            assessments.add(assessment); counts.merge(blockage, 1L, Long::sum);
        }
        assessments.sort(Comparator.comparing(QueueAssessment::blockage).thenComparing(QueueAssessment::queueKey));
        double pressure = capacity == 0 ? assessments.isEmpty() ? 0.0 : Double.POSITIVE_INFINITY
                : (double) assessments.size() / (double) capacity;
        return new QueueSummary(List.copyOf(assessments), assessments.size(), capacity, available, pressure, Map.copyOf(counts));
    }

    public List<BuildHealth> analyzeBuilds(Snapshot snapshot) {
        Map<String, List<BuildRecord>> byJob = new HashMap<>();
        snapshot.builds().values().forEach(build -> byJob.computeIfAbsent(build.jobKey(), ignored -> new ArrayList<>()).add(build));
        List<BuildHealth> result = new ArrayList<>();
        for (Map.Entry<String, List<BuildRecord>> entry : byJob.entrySet()) {
            int success = 0, unstable = 0, failed = 0, aborted = 0, running = 0, missing = 0, malformed = 0;
            long latest = 0; List<Long> durations = new ArrayList<>();
            for (BuildRecord build : entry.getValue()) {
                latest = Math.max(latest, build.startedMillis());
                switch (build.result()) {
                    case SUCCESS -> success++; case UNSTABLE -> unstable++; case FAILURE -> failed++;
                    case ABORTED, NOT_BUILT -> aborted++; case RUNNING -> running++; case MISSING -> missing++; case MALFORMED -> malformed++;
                }
                if (build.durationMillis() > 0) durations.add(build.durationMillis());
            }
            durations.sort(Long::compareTo); long median = durations.isEmpty() ? 0 : durations.get(durations.size() / 2);
            int completed = success + unstable + failed + aborted;
            double rate = completed == 0 ? 0.0 : (double) success / completed;
            result.add(new BuildHealth(entry.getKey(), entry.getValue().size(), success, unstable, failed,
                    aborted, running, missing, malformed, latest, median, rate));
        }
        result.sort(Comparator.comparing(BuildHealth::jobKey)); return List.copyOf(result);
    }

    public LineageSummary analyzeLineage(Snapshot snapshot) {
        List<LineageEdge> edges = new ArrayList<>(); int missingProducers = 0; int missingConsumers = 0;
        Map<String, Set<String>> graph = new HashMap<>(); Map<String, Integer> downstream = new TreeMap<>();
        for (FingerprintRecord fingerprint : snapshot.fingerprints().values()) {
            BuildRecord producer = snapshot.builds().get(fingerprint.producerBuildKey());
            if (producer == null) missingProducers++;
            for (String consumerKey : fingerprint.consumerBuildKeys()) {
                BuildRecord consumer = snapshot.builds().get(consumerKey); if (consumer == null) missingConsumers++;
                String producerJob = producer == null ? "" : producer.jobKey(); String consumerJob = consumer == null ? "" : consumer.jobKey();
                edges.add(new LineageEdge(fingerprint.key(), fingerprint.producerBuildKey(), consumerKey,
                        producerJob, consumerJob, producer == null, consumer == null));
                if (!producerJob.isBlank() && !consumerJob.isBlank()) {
                    graph.computeIfAbsent(producerJob, ignored -> new LinkedHashSet<>()).add(consumerJob);
                    downstream.merge(producerJob, 1, Integer::sum);
                }
            }
        }
        edges.sort(Comparator.comparing(LineageEdge::fingerprintKey).thenComparing(LineageEdge::consumerBuildKey));
        return new LineageSummary(List.copyOf(edges), snapshot.fingerprints().size(), missingProducers,
                missingConsumers, Map.copyOf(downstream), cycles(graph));
    }

    private List<List<String>> cycles(Map<String, Set<String>> graph) {
        List<List<String>> result = new ArrayList<>(); Set<String> complete = new HashSet<>(); Set<String> active = new HashSet<>();
        for (String node : new TreeMap<>(graph).keySet()) visit(node, graph, complete, active, new ArrayDeque<>(), result);
        return List.copyOf(result);
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
            PluginState state = plugin.enabled() ? PluginState.ENABLED : PluginState.DISABLED;
            PluginAssessment assessment = new PluginAssessment(plugin.key(), plugin.shortName(), plugin.version(), state,
                    plugin.bundled(), plugin.missingDependencies());
            assessments.add(assessment); counts.merge(state, 1L, Long::sum);
        }
        assessments.sort(Comparator.comparing(PluginAssessment::shortName));
        boolean restart = snapshot.plugins().values().stream().anyMatch(PluginRecord::restartPending);
        int missing = snapshot.plugins().values().stream().mapToInt(plugin -> plugin.missingDependencies().size()).sum();
        return new PluginSummary(List.copyOf(assessments), Map.copyOf(counts), restart, missing);
    }
}
