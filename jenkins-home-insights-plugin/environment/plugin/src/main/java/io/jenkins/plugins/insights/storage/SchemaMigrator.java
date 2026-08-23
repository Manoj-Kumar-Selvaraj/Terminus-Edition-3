package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Applies deterministic generation schema transformations. */
public final class SchemaMigrator {
    public record Migration(
            String generationId,
            int fromVersion,
            int toVersion,
            List<String> changedFiles,
            List<String> diagnostics) {
        public Migration {
            changedFiles = List.copyOf(changedFiles);
            diagnostics = List.copyOf(diagnostics);
        }

        public Map<String, Object> toMap() {
            return Domain.ordered(
                    "generationId", generationId,
                    "fromVersion", fromVersion,
                    "toVersion", toVersion,
                    "changedFiles", changedFiles,
                    "diagnostics", diagnostics);
        }
    }

    public Migration migrate(Path directory, int fromVersion, int toVersion) throws IOException {
        if (fromVersion < 1) {
            throw new IllegalArgumentException("source schema must be positive");
        }
        if (toVersion < fromVersion) {
            throw new IllegalArgumentException("schema downgrade is unsupported");
        }
        String generationId = directory.getFileName().toString();
        if (fromVersion == toVersion) {
            return new Migration(generationId, fromVersion, toVersion, List.of(), List.of("already current"));
        }

        List<String> changed = new ArrayList<>();
        List<String> diagnostics = new ArrayList<>();
        int version = fromVersion;
        while (version < toVersion) {
            if (version == 1) {
                migrateOneToTwo(directory, changed, diagnostics);
                version = 2;
            } else {
                throw new IOException("no migration path from schema " + version);
            }
        }
        return new Migration(generationId, fromVersion, version, changed, diagnostics);
    }

    @SuppressWarnings("unchecked")
    private void migrateOneToTwo(
            Path directory,
            List<String> changed,
            List<String> diagnostics) throws IOException {
        Path queue = directory.resolve("queues.json");
        if (Files.isRegularFile(queue)) {
            Object parsed = Json.parse(queue);
            if (!(parsed instanceof List<?> rows)) {
                throw new IOException("legacy queue file is not an array");
            }
            List<Object> migrated = new ArrayList<>();
            for (Object item : rows) {
                if (!(item instanceof Map<?, ?> raw)) {
                    diagnostics.add("ignored non-object queue row");
                    continue;
                }
                Map<String, Object> row = new LinkedHashMap<>((Map<String, Object>) raw);
                row.putIfAbsent("cancelled", false);
                row.putIfAbsent("blockageReason", "");
                migrated.add(row);
            }
            Json.write(queue, migrated);
            changed.add("queues.json");
        }

        Path plugins = directory.resolve("plugins.json");
        if (Files.isRegularFile(plugins)) {
            Object parsed = Json.parse(plugins);
            if (!(parsed instanceof List<?> rows)) {
                throw new IOException("legacy plugin file is not an array");
            }
            List<Object> migrated = new ArrayList<>();
            for (Object item : rows) {
                if (!(item instanceof Map<?, ?> raw)) {
                    diagnostics.add("ignored non-object plugin row");
                    continue;
                }
                Map<String, Object> row = new LinkedHashMap<>((Map<String, Object>) raw);
                row.putIfAbsent("compatible", true);
                row.putIfAbsent("restartPending", false);
                row.putIfAbsent("missingDependencies", List.of());
                migrated.add(row);
            }
            Json.write(plugins, migrated);
            changed.add("plugins.json");
        }
    }
}
