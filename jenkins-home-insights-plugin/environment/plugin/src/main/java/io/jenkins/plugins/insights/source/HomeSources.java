package io.jenkins.plugins.insights.source;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
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

/** Read-only adapters over the sanitized controller home's exported model. */
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
        public ScanResult {
            records = List.copyOf(records); errors = List.copyOf(errors);
        }
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
            forEachObject(context.home().resolve("exports/jobs.ndjson"), (row, line) -> {
                try {
                    String fullName = text(row, "fullName");
                    String leafName = fullName.substring(fullName.lastIndexOf('/') + 1);
                    String parent = fullName.contains("/") ? fullName.substring(0, fullName.lastIndexOf('/')) : "";
                    Identity identity = new Identity(SourceKind.JOB, leafName, text(row, "displayName", leafName), parent);
                    records.add(new JobRecord(identity, fullName, text(row, "url", "/job/" + fullName),
                            bool(row, "buildable", true), strings(row, "labels"),
                            state(row), context.sequence()));
                } catch (RuntimeException invalid) {
                    errors.add(error(SourceKind.JOB, row, line, "INVALID_JOB", invalid));
                }
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class BuildSource implements SourceAdapter<BuildRecord> {
        public SourceKind kind() { return SourceKind.BUILD; }
        public ScanResult<BuildRecord> scan(ScanContext context) throws IOException {
            List<BuildRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            try {
                forEachObject(context.home().resolve("exports/builds.ndjson"), (row, line) -> {
                    String jobKey = text(row, "jobKey"); long number = number(row, "number");
                    String key = jobKey + "#" + number;
                    Identity identity = new Identity(SourceKind.BUILD, key, text(row, "displayName", key), jobKey);
                    BuildResult result = enumValue(BuildResult.class, text(row, "result", "MISSING"));
                    records.add(new BuildRecord(identity, jobKey, number, number(row, "startedMillis"),
                            number(row, "durationMillis"), result, state(row), stringsList(row, "artifacts"),
                            context.sequence()));
                });
            } catch (RuntimeException invalid) {
                errors.add(new SourceError(SourceKind.BUILD, "", "BUILD_SCAN_ABORTED", invalid.getMessage()));
            }
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class QueueSource implements SourceAdapter<QueueRecord> {
        public SourceKind kind() { return SourceKind.QUEUE; }
        public ScanResult<QueueRecord> scan(ScanContext context) throws IOException {
            List<QueueRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/queue.ndjson"), (row, line) -> {
                try {
                    long itemId = number(row, "id"); String taskKey = text(row, "taskKey");
                    Identity identity = new Identity(SourceKind.QUEUE, Long.toString(itemId), taskKey + " queue item", taskKey);
                    records.add(new QueueRecord(identity, taskKey, strings(row, "labels"),
                            number(row, "enqueuedMillis"), bool(row, "cancelled", false),
                            text(row, "blockageReason", ""), context.sequence()));
                } catch (RuntimeException invalid) {
                    errors.add(error(SourceKind.QUEUE, row, line, "INVALID_QUEUE_ITEM", invalid));
                }
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class NodeSource implements SourceAdapter<NodeRecord> {
        public SourceKind kind() { return SourceKind.NODE; }
        public ScanResult<NodeRecord> scan(ScanContext context) throws IOException {
            List<NodeRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/nodes.ndjson"), (row, line) -> {
                try {
                    String name = text(row, "name");
                    Identity identity = new Identity(SourceKind.NODE, text(row, "id", name), name, "controller");
                    records.add(new NodeRecord(identity, strings(row, "labels"),
                            enumValue(NodeMode.class, text(row, "mode", "NORMAL")),
                            integer(row, "executors"), integer(row, "busyExecutors"),
                            bool(row, "online", true), bool(row, "acceptingTasks", true), context.sequence()));
                } catch (RuntimeException invalid) {
                    errors.add(error(SourceKind.NODE, row, line, "INVALID_NODE", invalid));
                }
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class FingerprintSource implements SourceAdapter<FingerprintRecord> {
        public SourceKind kind() { return SourceKind.FINGERPRINT; }
        public ScanResult<FingerprintRecord> scan(ScanContext context) throws IOException {
            Path capability = context.home().resolve("exports/fingerprint-capability.json");
            if (Files.exists(capability) && !bool(Json.object(capability), "enumeration", false)) {
                return new ScanResult<>(kind(), List.of(), List.of(), true);
            }
            List<FingerprintRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/fingerprints.ndjson"), (row, line) -> {
                try {
                    String hash = text(row, "hash"); String producer = text(row, "producerBuildKey", "");
                    Identity identity = new Identity(SourceKind.FINGERPRINT, hash, hash.substring(0, Math.min(12, hash.length())), producer);
                    records.add(new FingerprintRecord(identity, hash, producer, strings(row, "consumerBuildKeys"),
                            bool(row, "producerMissing", producer.isBlank()), context.sequence()));
                } catch (RuntimeException invalid) {
                    errors.add(error(SourceKind.FINGERPRINT, row, line, "INVALID_FINGERPRINT", invalid));
                }
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    public static final class PluginSource implements SourceAdapter<PluginRecord> {
        public SourceKind kind() { return SourceKind.PLUGIN; }
        public ScanResult<PluginRecord> scan(ScanContext context) throws IOException {
            List<PluginRecord> records = new ArrayList<>(); List<SourceError> errors = new ArrayList<>();
            forEachObject(context.home().resolve("exports/plugins.ndjson"), (row, line) -> {
                try {
                    String shortName = text(row, "shortName");
                    Identity identity = new Identity(SourceKind.PLUGIN, shortName, text(row, "displayName", shortName), "plugin-manager");
                    records.add(new PluginRecord(identity, shortName, text(row, "version", ""),
                            bool(row, "enabled", true), bool(row, "active", true),
                            bool(row, "bundled", false), bool(row, "compatible", true),
                            bool(row, "restartPending", false), strings(row, "missingDependencies"), context.sequence()));
                } catch (RuntimeException invalid) {
                    errors.add(error(SourceKind.PLUGIN, row, line, "INVALID_PLUGIN", invalid));
                }
            });
            return new ScanResult<>(kind(), records, errors, true);
        }
    }

    @FunctionalInterface
    private interface RowConsumer { void accept(Map<String, Object> row, long line) throws IOException; }

    private static void forEachObject(Path path, RowConsumer consumer) throws IOException {
        if (!Files.exists(path)) return;
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String line; long lineNumber = 0;
            while ((line = reader.readLine()) != null) {
                lineNumber++; if (line.isBlank()) continue;
                Object parsed = new LineParser(line).parse();
                if (!(parsed instanceof Map<?, ?> raw)) throw new IllegalArgumentException("line is not an object");
                Map<String, Object> row = new LinkedHashMap<>(); raw.forEach((key, value) -> row.put(String.valueOf(key), value));
                consumer.accept(row, lineNumber);
            }
        }
    }

    private static final class LineParser {
        private final String line;
        private LineParser(String line) { this.line = line; }
        private Object parse() throws IOException {
            Path temporary = Files.createTempFile("insights-row-", ".json");
            try { Files.writeString(temporary, line, StandardCharsets.UTF_8); return Json.parse(temporary); }
            finally { Files.deleteIfExists(temporary); }
        }
    }

    private static SourceError error(SourceKind kind, Map<String, Object> row, long line, String code, Exception error) {
        return new SourceError(kind, text(row, "id", "line:" + line), code,
                error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage());
    }
    private static RecordState state(Map<String, Object> row) { return enumValue(RecordState.class, text(row, "state", "ACTIVE")); }
    private static String text(Map<String, Object> row, String key) { return text(row, key, null); }
    private static String text(Map<String, Object> row, String key, String fallback) {
        Object value = row.get(key); if (value == null) { if (fallback != null) return fallback; throw new IllegalArgumentException(key + " is required"); }
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
