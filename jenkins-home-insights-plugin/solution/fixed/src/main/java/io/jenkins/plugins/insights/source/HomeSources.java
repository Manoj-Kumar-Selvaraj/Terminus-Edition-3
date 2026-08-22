package io.jenkins.plugins.insights.source;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain.BuildRecord;
import io.jenkins.plugins.insights.model.Domain.BuildResult;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.FingerprintRecord;
import io.jenkins.plugins.insights.model.Domain.Identity;
import io.jenkins.plugins.insights.model.Domain.JobRecord;
import io.jenkins.plugins.insights.model.Domain.NodeMode;
import io.jenkins.plugins.insights.model.Domain.NodeRecord;
import io.jenkins.plugins.insights.model.Domain.PluginRecord;
import io.jenkins.plugins.insights.model.Domain.QueueRecord;
import io.jenkins.plugins.insights.model.Domain.RecordState;
import io.jenkins.plugins.insights.model.Domain.SourceError;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public final class HomeSources {
    private HomeSources() {}

    public record ScanContext(Path home, long sequence, int batchSize) {
        public ScanContext {
            Objects.requireNonNull(home, "home");
            if (sequence < 0) throw new IllegalArgumentException("negative sequence");
            if (batchSize < 1) throw new IllegalArgumentException("batchSize must be positive");
        }
    }

    public record ScanResult<T extends CanonicalRecord>(SourceKind source, List<T> records,
                                                         List<SourceError> errors, boolean supported) {
        public ScanResult { records = List.copyOf(records); errors = List.copyOf(errors); }
    }

    public interface SourceAdapter<T extends CanonicalRecord> {
        SourceKind kind();
        ScanResult<T> scan(ScanContext context) throws IOException;
    }

    public static List<SourceAdapter<? extends CanonicalRecord>> standardAdapters() {
        return List.of(new JobSource(), new BuildSource(), new QueueSource(), new NodeSource(),
                new FingerprintSource(), new PluginSource());
    }

    public static final class JobSource implements SourceAdapter<JobRecord> {
        public SourceKind kind() { return SourceKind.JOB; }
        public ScanResult<JobRecord> scan(ScanContext context) throws IOException {
            List<JobRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/jobs.ndjson"), kind(), errors, (row, line) -> {
                String fullName = text(row, "fullName");
                String authorityKey = text(row, "id", fullName);
                String leafName = fullName.substring(fullName.lastIndexOf('/') + 1);
                String parent = fullName.contains("/") ? fullName.substring(0, fullName.lastIndexOf('/')) : "";
                Identity identity = new Identity(kind(), authorityKey, text(row, "displayName", leafName), parent);
                records.add(new JobRecord(identity, fullName, text(row, "url", "/job/" + fullName),
                        bool(row, "buildable", true), strings(row, "labels"), state(row), context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class BuildSource implements SourceAdapter<BuildRecord> {
        public SourceKind kind() { return SourceKind.BUILD; }
        public ScanResult<BuildRecord> scan(ScanContext context) throws IOException {
            List<BuildRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/builds.ndjson"), kind(), errors, (row, line) -> {
                String jobKey = text(row, "jobKey"); long number = number(row, "number");
                String key = text(row, "id", jobKey + "#" + number);
                Identity identity = new Identity(kind(), key, text(row, "displayName", "#" + number), jobKey);
                records.add(new BuildRecord(identity, jobKey, number, number(row, "startedMillis"),
                        number(row, "durationMillis"), enumValue(BuildResult.class, text(row, "result", "MISSING")),
                        state(row), stringsList(row, "artifacts"), context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class QueueSource implements SourceAdapter<QueueRecord> {
        public SourceKind kind() { return SourceKind.QUEUE; }
        public ScanResult<QueueRecord> scan(ScanContext context) throws IOException {
            List<QueueRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/queue.ndjson"), kind(), errors, (row, line) -> {
                long itemId = number(row, "id"); String taskKey = text(row, "taskKey");
                String key = Long.toString(itemId); String display = text(row, "displayName", taskKey + " queue item");
                Set<String> labels = strings(row, "labels"); long enqueued = number(row, "enqueuedMillis");
                boolean cancelled = bool(row, "cancelled", false); String reason = text(row, "blockageReason", "");
                records.add(new QueueRecord(new Identity(kind(), key, display, taskKey), taskKey, labels,
                        enqueued, cancelled, reason, context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class NodeSource implements SourceAdapter<NodeRecord> {
        public SourceKind kind() { return SourceKind.NODE; }
        public ScanResult<NodeRecord> scan(ScanContext context) throws IOException {
            List<NodeRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/nodes.ndjson"), kind(), errors, (row, line) -> {
                String name = text(row, "name"); String key = text(row, "id", name);
                Set<String> labels = strings(row, "labels"); NodeMode mode = enumValue(NodeMode.class, text(row, "mode", "NORMAL"));
                int executors = integer(row, "executors"); int busy = integer(row, "busyExecutors");
                boolean online = bool(row, "online", true); boolean accepting = bool(row, "acceptingTasks", true);
                records.add(new NodeRecord(new Identity(kind(), key, name, "controller"), labels, mode,
                        executors, busy, online, accepting, context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class FingerprintSource implements SourceAdapter<FingerprintRecord> {
        public SourceKind kind() { return SourceKind.FINGERPRINT; }
        public ScanResult<FingerprintRecord> scan(ScanContext context) throws IOException {
            Path capability = context.home().resolve("exports/fingerprint-capability.json");
            if (Files.isRegularFile(capability) && !bool(Json.object(capability), "enumeration", false)) {
                SourceError unavailable = new SourceError(kind(), "", "UNSUPPORTED_ENUMERATION",
                        "fingerprint provider does not support enumeration");
                return new ScanResult<>(kind(), List.of(), List.of(unavailable), false);
            }
            List<FingerprintRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/fingerprints.ndjson"), kind(), errors, (row, line) -> {
                String hash = text(row, "hash"); String producer = text(row, "producerBuildKey", "");
                String key = text(row, "id", hash);
                Identity identity = new Identity(kind(), key, hash.substring(0, Math.min(12, hash.length())), producer);
                records.add(new FingerprintRecord(identity, hash, producer, strings(row, "consumerBuildKeys"),
                        bool(row, "producerMissing", producer.isBlank()), context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class PluginSource implements SourceAdapter<PluginRecord> {
        public SourceKind kind() { return SourceKind.PLUGIN; }
        public ScanResult<PluginRecord> scan(ScanContext context) throws IOException {
            List<PluginRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/plugins.ndjson"), kind(), errors, (row, line) -> {
                String shortName = text(row, "shortName"); String key = text(row, "id", shortName);
                Identity identity = new Identity(kind(), key, text(row, "displayName", shortName), "plugin-manager");
                records.add(new PluginRecord(identity, shortName, text(row, "version", ""),
                        bool(row, "enabled", true), bool(row, "active", true), bool(row, "bundled", false),
                        bool(row, "compatible", true), bool(row, "restartPending", false),
                        strings(row, "missingDependencies"), context.sequence()));
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    @FunctionalInterface
    private interface RowConsumer { void accept(Map<String, Object> row, long line) throws IOException; }

    private static void forEachObject(Path path, SourceKind kind, List<SourceError> errors,
                                      RowConsumer consumer) throws IOException {
        if (!Files.exists(path)) return;
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String line; long lineNumber = 0;
            while ((line = reader.readLine()) != null) {
                lineNumber++; if (line.isBlank()) continue;
                Map<String, Object> row = new LinkedHashMap<>();
                try {
                    Path temporary = Files.createTempFile("insights-row-", ".json");
                    Object parsed;
                    try {
                        Files.writeString(temporary, line, StandardCharsets.UTF_8);
                        parsed = Json.parse(temporary);
                    } finally {
                        Files.deleteIfExists(temporary);
                    }
                    if (!(parsed instanceof Map<?, ?> raw)) throw new IllegalArgumentException("line is not an object");
                    raw.forEach((key, value) -> row.put(String.valueOf(key), value));
                    consumer.accept(Map.copyOf(row), lineNumber);
                } catch (RuntimeException | IOException invalid) {
                    errors.add(error(kind, row, lineNumber, "INVALID_" + kind.name(), invalid));
                }
            }
        }
    }

    private static SourceError error(SourceKind kind, Map<String, Object> row, long line, String code, Exception error) {
        return new SourceError(kind, text(row, "id", "line:" + line), code,
                error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage());
    }
    private static RecordState state(Map<String, Object> row) { return enumValue(RecordState.class, text(row, "state", "ACTIVE")); }
    private static String text(Map<String, Object> row, String key) { return text(row, key, null); }
    private static String text(Map<String, Object> row, String key, String fallback) {
        Object value = row.get(key);
        if (value == null) { if (fallback != null) return fallback; throw new IllegalArgumentException(key + " is required"); }
        return String.valueOf(value);
    }
    private static long number(Map<String, Object> row, String key) {
        Object value = row.get(key); if (value instanceof Number number) return number.longValue();
        return Long.parseLong(text(row, key));
    }
    private static int integer(Map<String, Object> row, String key) { return Math.toIntExact(number(row, key)); }
    private static boolean bool(Map<String, Object> row, String key, boolean fallback) {
        Object value = row.get(key); return value == null ? fallback : value instanceof Boolean flag ? flag : Boolean.parseBoolean(String.valueOf(value));
    }
    private static Set<String> strings(Map<String, Object> row, String key) { return new LinkedHashSet<>(stringsList(row, key)); }
    private static List<String> stringsList(Map<String, Object> row, String key) {
        Object value = row.get(key); if (!(value instanceof Collection<?> collection)) return List.of();
        return collection.stream().map(String::valueOf).toList();
    }
    private static <E extends Enum<E>> E enumValue(Class<E> type, String value) {
        return Enum.valueOf(type, value.trim().toUpperCase(Locale.ROOT).replace('-', '_'));
    }
}