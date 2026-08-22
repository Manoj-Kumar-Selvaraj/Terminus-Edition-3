package io.jenkins.plugins.insights.reconcile;

import io.jenkins.plugins.insights.model.Domain.*;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Converts journal and generation maps into typed canonical records. */
public final class RecordCodec {
    private RecordCodec() {}

    public static CanonicalRecord decode(SourceKind kind, Map<String, Object> row, long sequence) {
        return switch (kind) {
            case JOB -> job(row, sequence);
            case BUILD -> build(row, sequence);
            case QUEUE -> queue(row, sequence);
            case NODE -> node(row, sequence);
            case FINGERPRINT -> fingerprint(row, sequence);
            case PLUGIN -> plugin(row, sequence);
        };
    }

    public static JobRecord job(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.JOB);
        return new JobRecord(identity, text(row, "fullName", identity.displayName()), text(row, "url", ""),
                bool(row, "buildable", true), strings(row, "labels"), state(row), sequence);
    }

    public static BuildRecord build(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.BUILD); String jobKey = text(row, "jobKey", identity.parentKey());
        return new BuildRecord(identity, jobKey, number(row, "number", 0), number(row, "startedMillis", 0),
                number(row, "durationMillis", 0), enumeration(BuildResult.class, text(row, "result", "MISSING")),
                state(row), List.copyOf(strings(row, "artifacts")), sequence);
    }

    public static QueueRecord queue(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.QUEUE); String task = text(row, "taskKey", identity.parentKey());
        return new QueueRecord(identity, task, strings(row, "labels"), number(row, "enqueuedMillis", 0),
                bool(row, "cancelled", false), text(row, "blockageReason", ""), sequence);
    }

    public static NodeRecord node(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.NODE);
        return new NodeRecord(identity, strings(row, "labels"), enumeration(NodeMode.class, text(row, "mode", "NORMAL")),
                integer(row, "executors", 0), integer(row, "busyExecutors", 0), bool(row, "online", true),
                bool(row, "acceptingTasks", true), sequence);
    }

    public static FingerprintRecord fingerprint(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.FINGERPRINT); String producer = text(row, "producerBuildKey", identity.parentKey());
        return new FingerprintRecord(identity, text(row, "hash", identity.stableKey()), producer,
                strings(row, "consumerBuildKeys"), bool(row, "producerMissing", producer.isBlank()), sequence);
    }

    public static PluginRecord plugin(Map<String, Object> row, long sequence) {
        Identity identity = identity(row, SourceKind.PLUGIN); String shortName = text(row, "shortName", identity.stableKey());
        return new PluginRecord(identity, shortName, text(row, "version", ""), bool(row, "enabled", true),
                bool(row, "active", true), bool(row, "bundled", false), bool(row, "compatible", true),
                bool(row, "restartPending", false), strings(row, "missingDependencies"), sequence);
    }

    @SuppressWarnings("unchecked")
    public static Identity identity(Map<String, Object> row, SourceKind kind) {
        if (row.get("identity") instanceof Map<?, ?> nested) {
            Map<String, Object> identity = (Map<String, Object>) nested;
            return new Identity(kind, text(identity, "key", ""), text(identity, "display", ""), text(identity, "parent", ""));
        }
        String key = text(row, "key", text(row, "id", ""));
        return new Identity(kind, key, text(row, "displayName", key), text(row, "parentKey", ""));
    }

    public static String text(Map<String, Object> row, String key, String fallback) {
        Object value = row.get(key); return value == null ? fallback : String.valueOf(value);
    }
    public static long number(Map<String, Object> row, String key, long fallback) {
        Object value = row.get(key); if (value == null) return fallback;
        return value instanceof Number number ? number.longValue() : Long.parseLong(String.valueOf(value));
    }
    public static int integer(Map<String, Object> row, String key, int fallback) { return Math.toIntExact(number(row, key, fallback)); }
    public static boolean bool(Map<String, Object> row, String key, boolean fallback) {
        Object value = row.get(key); return value == null ? fallback : value instanceof Boolean flag ? flag : Boolean.parseBoolean(String.valueOf(value));
    }
    public static Set<String> strings(Map<String, Object> row, String key) {
        Object value = row.get(key); if (!(value instanceof Collection<?> values)) return Set.of();
        Set<String> result = new LinkedHashSet<>(); values.forEach(item -> result.add(String.valueOf(item))); return result;
    }
    public static RecordState state(Map<String, Object> row) { return enumeration(RecordState.class, text(row, "state", "ACTIVE")); }
    public static <E extends Enum<E>> E enumeration(Class<E> type, String value) {
        return Enum.valueOf(type, value.toUpperCase(Locale.ROOT).replace('-', '_'));
    }
}
