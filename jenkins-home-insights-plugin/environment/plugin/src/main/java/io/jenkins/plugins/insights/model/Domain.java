package io.jenkins.plugins.insights.model;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;

/** Canonical records shared by collection, reduction, persistence, and query. */
public final class Domain {
    private Domain() {}

    public enum SourceKind { JOB, BUILD, QUEUE, NODE, FINGERPRINT, PLUGIN }
    public enum RecordState { ACTIVE, RUNNING, CANCELLED, DELETED, MALFORMED, UNSUPPORTED }
    public enum BuildResult { SUCCESS, UNSTABLE, FAILURE, ABORTED, NOT_BUILT, RUNNING, MISSING, MALFORMED }
    public enum NodeMode { NORMAL, EXCLUSIVE }
    public enum QueueBlockage { RUNNABLE, LABEL_MISMATCH, NO_EXECUTOR, OFFLINE, EXCLUSIVE_REJECTED, CANCELLED }
    public enum PluginState { ENABLED, DISABLED, FAILED, BUNDLED, INCOMPATIBLE, DEPENDENCY_MISSING, RESTART_PENDING }
    public enum EventOperation { UPSERT, DELETE, DIRTY }

    public record Identity(SourceKind kind, String stableKey, String displayName, String parentKey) {
        public Identity {
            Objects.requireNonNull(kind, "kind");
            stableKey = requireText(stableKey, "stableKey");
            displayName = displayName == null ? "" : displayName;
            parentKey = parentKey == null ? "" : parentKey;
        }
        public String externalKey() { return kind.name().toLowerCase(Locale.ROOT) + ":" + stableKey; }
        public Map<String, Object> toMap() {
            return ordered("kind", kind.name(), "key", stableKey, "display", displayName, "parent", parentKey);
        }
    }

    public record SourceError(SourceKind source, String recordKey, String code, String message) {
        public SourceError {
            Objects.requireNonNull(source, "source");
            recordKey = recordKey == null ? "" : recordKey;
            code = requireText(code, "code");
            message = message == null ? "" : message;
        }
        public Map<String, Object> toMap() {
            return ordered("source", source.name(), "recordKey", recordKey, "code", code, "message", message);
        }
    }

    public record JobRecord(Identity identity, String fullName, String url, boolean buildable,
                            Set<String> labels, RecordState state, long observedSequence) implements CanonicalRecord {
        public JobRecord {
            Objects.requireNonNull(identity, "identity");
            fullName = requireText(fullName, "fullName");
            url = url == null ? "" : url;
            labels = immutableSorted(labels);
            Objects.requireNonNull(state, "state");
        }
        public SourceKind kind() { return SourceKind.JOB; }
        public String key() { return identity.stableKey(); }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "fullName", fullName, "url", url, "buildable", buildable,
                    "labels", labels, "state", state.name(), "sequence", observedSequence);
        }
    }

    public record BuildRecord(Identity identity, String jobKey, long number, long startedMillis,
                              long durationMillis, BuildResult result, RecordState state,
                              List<String> artifactIds, long observedSequence) implements CanonicalRecord {
        public BuildRecord {
            Objects.requireNonNull(identity, "identity");
            jobKey = requireText(jobKey, "jobKey");
            Objects.requireNonNull(result, "result");
            Objects.requireNonNull(state, "state");
            artifactIds = immutableSortedList(artifactIds);
        }
        public SourceKind kind() { return SourceKind.BUILD; }
        public String key() { return identity.stableKey(); }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "jobKey", jobKey, "number", number,
                    "startedMillis", startedMillis, "durationMillis", durationMillis, "result", result.name(),
                    "state", state.name(), "artifacts", artifactIds, "sequence", observedSequence);
        }
    }

    public record QueueRecord(Identity identity, String taskKey, Set<String> labels, long enqueuedMillis,
                              boolean cancelled, String blockageReason, long observedSequence) implements CanonicalRecord {
        public QueueRecord {
            Objects.requireNonNull(identity, "identity");
            taskKey = requireText(taskKey, "taskKey");
            labels = immutableSorted(labels);
            blockageReason = blockageReason == null ? "" : blockageReason;
        }
        public SourceKind kind() { return SourceKind.QUEUE; }
        public String key() { return identity.stableKey(); }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "taskKey", taskKey, "labels", labels,
                    "enqueuedMillis", enqueuedMillis, "cancelled", cancelled,
                    "blockageReason", blockageReason, "sequence", observedSequence);
        }
    }

    public record NodeRecord(Identity identity, Set<String> labels, NodeMode mode, int executors,
                             int busyExecutors, boolean online, boolean acceptingTasks,
                             long observedSequence) implements CanonicalRecord {
        public NodeRecord {
            Objects.requireNonNull(identity, "identity");
            labels = immutableSorted(labels);
            Objects.requireNonNull(mode, "mode");
            if (executors < 0 || busyExecutors < 0) throw new IllegalArgumentException("negative executors");
        }
        public SourceKind kind() { return SourceKind.NODE; }
        public String key() { return identity.stableKey(); }
        public int availableExecutors() { return online && acceptingTasks ? Math.max(0, executors - busyExecutors) : 0; }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "labels", labels, "mode", mode.name(),
                    "executors", executors, "busyExecutors", busyExecutors, "online", online,
                    "acceptingTasks", acceptingTasks, "sequence", observedSequence);
        }
    }

    public record FingerprintRecord(Identity identity, String hash, String producerBuildKey,
                                    Set<String> consumerBuildKeys, boolean producerMissing,
                                    long observedSequence) implements CanonicalRecord {
        public FingerprintRecord {
            Objects.requireNonNull(identity, "identity");
            hash = requireText(hash, "hash");
            producerBuildKey = producerBuildKey == null ? "" : producerBuildKey;
            consumerBuildKeys = immutableSorted(consumerBuildKeys);
        }
        public SourceKind kind() { return SourceKind.FINGERPRINT; }
        public String key() { return identity.stableKey(); }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "hash", hash, "producerBuildKey", producerBuildKey,
                    "consumerBuildKeys", consumerBuildKeys, "producerMissing", producerMissing,
                    "sequence", observedSequence);
        }
    }

    public record PluginRecord(Identity identity, String shortName, String version, boolean enabled,
                               boolean active, boolean bundled, boolean compatible,
                               boolean restartPending, Set<String> missingDependencies,
                               long observedSequence) implements CanonicalRecord {
        public PluginRecord {
            Objects.requireNonNull(identity, "identity");
            shortName = requireText(shortName, "shortName");
            version = version == null ? "" : version;
            missingDependencies = immutableSorted(missingDependencies);
        }
        public SourceKind kind() { return SourceKind.PLUGIN; }
        public String key() { return identity.stableKey(); }
        public Map<String, Object> toMap() {
            return ordered("identity", identity.toMap(), "shortName", shortName, "version", version,
                    "enabled", enabled, "active", active, "bundled", bundled, "compatible", compatible,
                    "restartPending", restartPending, "missingDependencies", missingDependencies,
                    "sequence", observedSequence);
        }
    }

    public sealed interface CanonicalRecord permits JobRecord, BuildRecord, QueueRecord, NodeRecord,
            FingerprintRecord, PluginRecord {
        SourceKind kind();
        String key();
        long observedSequence();
        Map<String, Object> toMap();
    }

    public record Event(long sequence, String eventId, SourceKind source, EventOperation operation,
                        String recordKey, String payloadHash, Map<String, Object> payload) {
        public Event {
            if (sequence < 0) throw new IllegalArgumentException("negative event sequence");
            eventId = requireText(eventId, "eventId");
            Objects.requireNonNull(source, "source");
            Objects.requireNonNull(operation, "operation");
            recordKey = requireText(recordKey, "recordKey");
            payloadHash = requireText(payloadHash, "payloadHash");
            payload = immutableMap(payload);
        }
        public Map<String, Object> toMap() {
            return ordered("sequence", sequence, "eventId", eventId, "source", source.name(),
                    "operation", operation.name(), "recordKey", recordKey,
                    "payloadHash", payloadHash, "payload", payload);
        }
    }

    public record Checkpoint(long appliedSequence, String generationId, String digest) {
        public Checkpoint {
            if (appliedSequence < 0) throw new IllegalArgumentException("negative checkpoint");
            generationId = generationId == null ? "" : generationId;
            digest = digest == null ? "" : digest;
        }
        public Map<String, Object> toMap() {
            return ordered("appliedSequence", appliedSequence, "generationId", generationId, "digest", digest);
        }
    }

    public record Snapshot(Map<String, JobRecord> jobs, Map<String, BuildRecord> builds,
                           Map<String, QueueRecord> queue, Map<String, NodeRecord> nodes,
                           Map<String, FingerprintRecord> fingerprints, Map<String, PluginRecord> plugins,
                           List<SourceError> errors, Set<SourceKind> unsupportedSources,
                           Checkpoint checkpoint) {
        public Snapshot {
            jobs = immutableMap(jobs); builds = immutableMap(builds); queue = immutableMap(queue);
            nodes = immutableMap(nodes); fingerprints = immutableMap(fingerprints); plugins = immutableMap(plugins);
            errors = List.copyOf(errors == null ? List.of() : errors);
            unsupportedSources = immutableSorted(unsupportedSources);
            checkpoint = checkpoint == null ? new Checkpoint(0, "", "") : checkpoint;
        }
        public static Snapshot empty() {
            return new Snapshot(Map.of(), Map.of(), Map.of(), Map.of(), Map.of(), Map.of(),
                    List.of(), Set.of(), new Checkpoint(0, "", ""));
        }
        public int recordCount() {
            return jobs.size() + builds.size() + queue.size() + nodes.size() + fingerprints.size() + plugins.size();
        }
        public Collection<CanonicalRecord> allRecords() {
            List<CanonicalRecord> records = new ArrayList<>(recordCount());
            records.addAll(jobs.values()); records.addAll(builds.values()); records.addAll(queue.values());
            records.addAll(nodes.values()); records.addAll(fingerprints.values()); records.addAll(plugins.values());
            records.sort(Comparator.comparing((CanonicalRecord r) -> r.kind().name()).thenComparing(CanonicalRecord::key));
            return List.copyOf(records);
        }
        public Map<String, Object> toMap() {
            return ordered("jobs", maps(jobs.values()), "builds", maps(builds.values()),
                    "queue", maps(queue.values()), "nodes", maps(nodes.values()),
                    "fingerprints", maps(fingerprints.values()), "plugins", maps(plugins.values()),
                    "errors", errors.stream().map(SourceError::toMap).toList(),
                    "unsupportedSources", unsupportedSources.stream().map(Enum::name).toList(),
                    "checkpoint", checkpoint.toMap());
        }
    }

    public record GenerationManifest(int schemaVersion, String generationId, long createdEpochMillis,
                                     long firstSequence, long lastSequence, int recordCount,
                                     Map<String, String> checksums, String contentDigest) {
        public GenerationManifest {
            if (schemaVersion < 1) throw new IllegalArgumentException("invalid schema version");
            generationId = requireText(generationId, "generationId");
            checksums = immutableMap(checksums);
            contentDigest = requireText(contentDigest, "contentDigest");
        }
        public Map<String, Object> toMap() {
            return ordered("schemaVersion", schemaVersion, "generationId", generationId,
                    "createdEpochMillis", createdEpochMillis, "firstSequence", firstSequence,
                    "lastSequence", lastSequence, "recordCount", recordCount,
                    "checksums", checksums, "contentDigest", contentDigest);
        }
    }

    public record Page<T>(List<T> items, int total, String nextCursor, Map<String, Long> facets) {
        public Page {
            items = List.copyOf(items == null ? List.of() : items);
            nextCursor = nextCursor == null ? "" : nextCursor;
            facets = immutableMap(facets);
        }
    }

    public static String stableId(SourceKind kind, String authorityKey) {
        return kind.name().toLowerCase(Locale.ROOT) + "-" + sha256(authorityKey).substring(0, 24);
    }

    public static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(64);
            for (byte item : digest) result.append(String.format(Locale.ROOT, "%02x", item));
            return result.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public static String requireText(String value, String field) {
        if (value == null || value.isBlank()) throw new IllegalArgumentException(field + " is required");
        return value;
    }

    public static <T> Set<T> immutableSorted(Collection<T> values) {
        if (values == null || values.isEmpty()) return Set.of();
        List<T> sorted = new ArrayList<>(values);
        sorted.sort(Comparator.comparing(String::valueOf));
        return java.util.Collections.unmodifiableSet(new LinkedHashSet<>(sorted));
    }

    public static <T> List<T> immutableSortedList(Collection<T> values) {
        if (values == null || values.isEmpty()) return List.of();
        List<T> sorted = new ArrayList<>(values);
        sorted.sort(Comparator.comparing(String::valueOf));
        return List.copyOf(sorted);
    }

    public static <K, V> Map<K, V> immutableMap(Map<K, V> values) {
        if (values == null || values.isEmpty()) return Map.of();
        Map<K, V> sorted = new TreeMap<>(Comparator.comparing(String::valueOf));
        sorted.putAll(values);
        return java.util.Collections.unmodifiableMap(sorted);
    }

    public static Map<String, Object> ordered(Object... pairs) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int index = 0; index < pairs.length; index += 2) result.put(String.valueOf(pairs[index]), pairs[index + 1]);
        return result;
    }

    private static List<Map<String, Object>> maps(Collection<? extends CanonicalRecord> records) {
        return records.stream().sorted(Comparator.comparing(CanonicalRecord::key)).map(CanonicalRecord::toMap).toList();
    }
}
