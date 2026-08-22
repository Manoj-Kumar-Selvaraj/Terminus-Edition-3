package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.json.CanonicalJson;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.*;
import io.jenkins.plugins.insights.reconcile.RecordCodec;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

/** Versioned derived-state repository. Jenkins-owned files are never modified. */
public final class GenerationStore {
    public static final int CURRENT_SCHEMA = 2;
    private static final List<SourceKind> TYPES = List.of(SourceKind.JOB, SourceKind.BUILD, SourceKind.QUEUE,
            SourceKind.NODE, SourceKind.FINGERPRINT, SourceKind.PLUGIN);
    private final Path state;
    private final Path generations;
    private final AtomicLong identifiers = new AtomicLong();

    public GenerationStore(Path state) throws IOException {
        this.state = state.toAbsolutePath().normalize(); this.generations = this.state.resolve("generations");
        Files.createDirectories(generations); Files.createDirectories(this.state.resolve("leases"));
    }

    public record Published(String generationId, GenerationManifest manifest, Snapshot snapshot) {}
    public record Verification(boolean valid, List<String> errors, GenerationManifest manifest) {}
    public record RecoverySelection(String generationId, Snapshot snapshot, List<String> diagnostics) {}
    public record RetentionResult(List<String> retained, List<String> deleted, List<String> leased) {}

    public synchronized Published publish(Snapshot snapshot, Map<String, Object> analysis) throws IOException {
        String generationId = nextId(snapshot.checkpoint().appliedSequence());
        Path staging = generations.resolve("." + generationId + ".staging"); Path destination = generations.resolve(generationId);
        deleteTree(staging); Files.createDirectories(staging);
        Map<String, String> checksums = new TreeMap<>();
        for (SourceKind type : TYPES) {
            Path file = staging.resolve(fileName(type)); List<Map<String, Object>> rows = rows(snapshot, type);
            CanonicalJson.write(file, rows); checksums.put(file.getFileName().toString(), checksum(file));
        }
        Json.write(staging.resolve("errors.json"), snapshot.errors().stream().map(SourceError::toMap).toList());
        Json.write(staging.resolve("analysis.json"), analysis); Json.write(staging.resolve("checkpoint.json"), snapshot.checkpoint().toMap());
        checksums.put("errors.json", checksum(staging.resolve("errors.json")));
        checksums.put("analysis.json", checksum(staging.resolve("analysis.json")));
        checksums.put("checkpoint.json", checksum(staging.resolve("checkpoint.json")));
        String contentDigest = CanonicalJson.document(checksums, checksums.size()).sha256();
        GenerationManifest manifest = new GenerationManifest(CURRENT_SCHEMA, generationId, deterministicTimestamp(generationId),
                0, snapshot.checkpoint().appliedSequence(), snapshot.recordCount(), checksums, contentDigest);
        Json.write(staging.resolve("manifest.json"), manifest.toMap());
        move(staging, destination); writeCurrent(generationId);
        Verification verification = verify(destination);
        if (!verification.valid()) throw new IOException("published generation did not verify: " + verification.errors());
        return new Published(generationId, manifest, snapshot);
    }

    public Optional<String> currentId() throws IOException {
        Path pointer = state.resolve("CURRENT");
        if (!Files.exists(pointer)) return Optional.empty();
        String value = Files.readString(pointer, StandardCharsets.UTF_8).trim();
        return value.isBlank() ? Optional.empty() : Optional.of(value);
    }

    public Snapshot loadCurrent() throws IOException {
        String id = currentId().orElseThrow(() -> new IOException("CURRENT is absent")); return load(generations.resolve(id));
    }

    public RecoverySelection recover() throws IOException {
        List<Path> candidates = listGenerations();
        if (candidates.isEmpty()) return new RecoverySelection("", Snapshot.empty(), List.of("no generation available"));
        RecoveryPlanner.Plan plan = new RecoveryPlanner().plan(candidates, currentId().orElse(""), this);
        Path selected = plan.selected().directory();
        writeCurrent(selected.getFileName().toString());
        return new RecoverySelection(selected.getFileName().toString(), load(selected), List.of(plan.reason()));
    }

    public Verification verifyCurrent() throws IOException {
        Optional<String> current = currentId();
        return current.isEmpty() ? new Verification(false, List.of("CURRENT is absent"), null)
                : verify(generations.resolve(current.get()));
    }

    public Verification verify(Path directory) throws IOException {
        List<String> errors = new ArrayList<>(); Path manifestPath = directory.resolve("manifest.json");
        if (!Files.exists(manifestPath)) return new Verification(false, List.of("manifest is absent"), null);
        GenerationManifest manifest;
        try { manifest = manifest(Json.object(manifestPath)); }
        catch (RuntimeException invalid) { return new Verification(false, List.of("manifest invalid: " + invalid.getMessage()), null); }
        for (Map.Entry<String, String> expected : manifest.checksums().entrySet()) {
            Path file = directory.resolve(expected.getKey());
            if (!Files.isRegularFile(file)) errors.add("missing " + expected.getKey());
            else if (!checksum(file).equals(expected.getValue())) errors.add("checksum mismatch " + expected.getKey());
        }
        if (!Domain.sha256(Json.write(manifest.checksums())).equals(manifest.contentDigest())) errors.add("content digest mismatch");
        if (manifest.firstSequence() > manifest.lastSequence()) errors.add("checkpoint bounds reversed");
        return new Verification(errors.isEmpty(), List.copyOf(errors), manifest);
    }

    public synchronized String migrate(String generationId) throws IOException {
        Path directory = generations.resolve(generationId); GenerationManifest old = manifest(Json.object(directory.resolve("manifest.json")));
        if (old.schemaVersion() >= CURRENT_SCHEMA) return generationId;
        new SchemaMigrator().migrate(directory, old.schemaVersion(), CURRENT_SCHEMA);
        Map<String, Object> updated = new LinkedHashMap<>(old.toMap()); updated.put("schemaVersion", CURRENT_SCHEMA);
        Json.write(directory.resolve("manifest.json"), updated); return generationId;
    }

    public Lease lease(String generationId, String owner) throws IOException {
        Path lease = state.resolve("leases").resolve(generationId + "--" + sanitize(owner) + ".lease");
        Files.writeString(lease, generationId + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
        return new Lease(lease);
    }

    public RetentionResult compact(int retain) throws IOException {
        if (retain < 1) throw new IllegalArgumentException("retain must be positive");
        List<Path> candidates = listGenerations(); Set<String> leasedIds = leasedIds();
        RetentionPlanner.Plan plan = new RetentionPlanner().plan(candidates, currentId().orElse(""), leasedIds,
            retain, new RetentionPlanner().readReferences(candidates));
        List<String> retained = new ArrayList<>(); List<String> deleted = new ArrayList<>();
        int boundary = Math.max(0, candidates.size() - retain);
        for (int index = 0; index < candidates.size(); index++) {
            String id = candidates.get(index).getFileName().toString();
            if (index >= boundary) retained.add(id); else { deleteTree(candidates.get(index)); deleted.add(id); }
        }
        return new RetentionResult(List.copyOf(retained), List.copyOf(deleted), leasedIds.stream().sorted().toList());
    }

    public List<String> inventory() throws IOException { return listGenerations().stream().map(path -> path.getFileName().toString()).toList(); }

    @SuppressWarnings("unchecked")
    public Snapshot load(Path directory) throws IOException {
        Map<String, JobRecord> jobs = new LinkedHashMap<>(); Map<String, BuildRecord> builds = new LinkedHashMap<>();
        Map<String, QueueRecord> queue = new LinkedHashMap<>(); Map<String, NodeRecord> nodes = new LinkedHashMap<>();
        Map<String, FingerprintRecord> fingerprints = new LinkedHashMap<>(); Map<String, PluginRecord> plugins = new LinkedHashMap<>();
        for (SourceKind type : TYPES) {
            Object parsed = Json.parse(directory.resolve(fileName(type)));
            if (!(parsed instanceof List<?> list)) throw new IOException("typed file is not an array: " + type);
            for (Object item : list) {
                if (!(item instanceof Map<?, ?> raw)) throw new IOException("typed record is not an object: " + type);
                CanonicalRecord record = RecordCodec.decode(type, (Map<String, Object>) raw, RecordCodec.number((Map<String, Object>) raw, "sequence", 0));
                if (record instanceof JobRecord value) jobs.put(value.key(), value);
                else if (record instanceof BuildRecord value) builds.put(value.key(), value);
                else if (record instanceof QueueRecord value) queue.put(value.key(), value);
                else if (record instanceof NodeRecord value) nodes.put(value.key(), value);
                else if (record instanceof FingerprintRecord value) fingerprints.put(value.key(), value);
                else if (record instanceof PluginRecord value) plugins.put(value.key(), value);
            }
        }
        List<SourceError> errors = new ArrayList<>();
        Object errorData = Json.parse(directory.resolve("errors.json"));
        if (errorData instanceof List<?> list) for (Object item : list) if (item instanceof Map<?, ?> raw) {
            Map<String, Object> row = (Map<String, Object>) raw;
            errors.add(new SourceError(SourceKind.valueOf(RecordCodec.text(row, "source", "JOB")),
                    RecordCodec.text(row, "recordKey", ""), RecordCodec.text(row, "code", "UNKNOWN"),
                    RecordCodec.text(row, "message", "")));
        }
        Map<String, Object> checkpointData = Json.object(directory.resolve("checkpoint.json"));
        Checkpoint checkpoint = new Checkpoint(RecordCodec.number(checkpointData, "appliedSequence", 0),
                RecordCodec.text(checkpointData, "generationId", directory.getFileName().toString()),
                RecordCodec.text(checkpointData, "digest", ""));
        return new Snapshot(jobs, builds, queue, nodes, fingerprints, plugins, errors, Set.of(), checkpoint);
    }

    private List<Map<String, Object>> rows(Snapshot snapshot, SourceKind type) {
        Collection<? extends CanonicalRecord> records = switch (type) {
            case JOB -> snapshot.jobs().values(); case BUILD -> snapshot.builds().values(); case QUEUE -> snapshot.queue().values();
            case NODE -> snapshot.nodes().values(); case FINGERPRINT -> snapshot.fingerprints().values(); case PLUGIN -> snapshot.plugins().values();
        };
        return records.stream().sorted(Comparator.comparing(CanonicalRecord::key)).map(CanonicalRecord::toMap).toList();
    }

    private String nextId(long sequence) {
        long ordinal = identifiers.incrementAndGet(); return String.format("gen-%012d-%04d", sequence, ordinal);
    }
    private long deterministicTimestamp(String generationId) { return 1_735_689_600_000L + Math.abs(generationId.hashCode()); }
    private String fileName(SourceKind kind) { return kind.name().toLowerCase() + "s.json"; }
    private String checksum(Path path) throws IOException { return Domain.sha256(Files.readString(path, StandardCharsets.UTF_8)); }
    private void writeCurrent(String id) throws IOException {
        Path temporary = state.resolve("CURRENT.tmp"); Files.writeString(temporary, id + "\n", StandardCharsets.UTF_8);
        move(temporary, state.resolve("CURRENT"));
    }
    private void move(Path from, Path to) throws IOException {
        try { Files.move(from, to, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
        catch (AtomicMoveNotSupportedException unsupported) { Files.move(from, to, StandardCopyOption.REPLACE_EXISTING); }
    }
    private List<Path> listGenerations() throws IOException {
        List<Path> result = new ArrayList<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(generations, "gen-*")) {
            for (Path path : stream) if (Files.isDirectory(path)) result.add(path);
        }
        result.sort(Comparator.comparing(path -> path.getFileName().toString())); return result;
    }
    private Set<String> leasedIds() throws IOException {
        Set<String> result = new java.util.HashSet<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(state.resolve("leases"), "*.lease")) {
            for (Path path : stream) result.add(path.getFileName().toString().split("--", 2)[0]);
        }
        return Set.copyOf(result);
    }
    private String sanitize(String value) { return value.replaceAll("[^A-Za-z0-9_.-]", "_"); }
    private GenerationManifest manifest(Map<String, Object> row) {
        Map<String, String> checksums = new TreeMap<>();
        if (row.get("checksums") instanceof Map<?, ?> raw) raw.forEach((key, value) -> checksums.put(String.valueOf(key), String.valueOf(value)));
        return new GenerationManifest(RecordCodec.integer(row, "schemaVersion", 1), RecordCodec.text(row, "generationId", ""),
                RecordCodec.number(row, "createdEpochMillis", 0), RecordCodec.number(row, "firstSequence", 0),
                RecordCodec.number(row, "lastSequence", 0), RecordCodec.integer(row, "recordCount", 0), checksums,
                RecordCodec.text(row, "contentDigest", ""));
    }
    private void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        try (var paths = Files.walk(root)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path);
        }
    }

    public static final class Lease implements AutoCloseable {
        private final Path path; private Lease(Path path) { this.path = path; }
        public Path path() { return path; }
        @Override public void close() throws IOException { Files.deleteIfExists(path); }
    }
}