package io.jenkins.plugins.insights.json;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.Snapshot;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Canonical JSON projection used by storage digests and transport output. */
public final class CanonicalJson {
    public record Document(String json, String sha256, int records, int bytes) {}
    private CanonicalJson() {}

    public static Document snapshot(Snapshot snapshot) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("jobs", records(snapshot.jobs().values())); root.put("builds", records(snapshot.builds().values()));
        root.put("queue", records(snapshot.queue().values())); root.put("nodes", records(snapshot.nodes().values()));
        root.put("fingerprints", records(snapshot.fingerprints().values())); root.put("plugins", records(snapshot.plugins().values()));
        root.put("errors", normalize(snapshot.errors().stream().map(Domain.SourceError::toMap).toList()));
        root.put("unsupportedSources", snapshot.unsupportedSources().stream().map(Enum::name).sorted().toList());
        root.put("checkpoint", normalize(snapshot.checkpoint().toMap()));
        return document(root, snapshot.recordCount());
    }

    public static Document document(Object value, int records) {
        Object normalized = normalize(value); String json = Json.write(normalized);
        int bytes = json.getBytes(StandardCharsets.UTF_8).length;
        return new Document(json, Domain.sha256(json), records, bytes);
    }

    public static void write(Path path, Object value) throws IOException {
        Document document = document(value, value instanceof Collection<?> collection ? collection.size() : 1);
        Files.createDirectories(path.toAbsolutePath().getParent());
        Files.writeString(path, document.json() + "\n", StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    public static Object normalize(Object value) {
        if (value == null || value instanceof String || value instanceof Boolean) return value;
        if (value instanceof Enum<?> enumeration) return enumeration.name();
        if (value instanceof Number number) {
            if (number instanceof Double decimal && !Double.isFinite(decimal)) return decimal > 0 ? "unbounded" : "undefined";
            if (number instanceof Float decimal && !Float.isFinite(decimal)) return decimal > 0 ? "unbounded" : "undefined";
            return number;
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> sorted = new TreeMap<>();
            map.forEach((key, item) -> sorted.put(String.valueOf(key), normalize(item))); return sorted;
        }
        if (value instanceof Collection<?> collection) {
            List<Object> normalized = new ArrayList<>(collection.size());
            for (Object item : collection) normalized.add(normalize(item)); return List.copyOf(normalized);
        }
        if (value.getClass().isArray()) {
            List<Object> normalized = new ArrayList<>();
            for (int index = 0; index < java.lang.reflect.Array.getLength(value); index++)
                normalized.add(normalize(java.lang.reflect.Array.get(value, index)));
            return List.copyOf(normalized);
        }
        if (value instanceof CanonicalRecord record) return normalize(record.toMap());
        throw new IllegalArgumentException("unsupported canonical value: " + value.getClass().getName());
    }

    private static List<Map<String, Object>> records(Collection<? extends CanonicalRecord> values) {
        return values.stream().sorted(Comparator.comparing(CanonicalRecord::key))
                .map(record -> cast(normalize(record.toMap()))).toList();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> cast(Object value) { return (Map<String, Object>) value; }
}
