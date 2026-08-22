package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.json.CanonicalJson;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.*;
import io.jenkins.plugins.insights.reconcile.RecordCodec;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

public final class GenerationStore {
    public static final int CURRENT_SCHEMA = 2;
    private static final List<SourceKind> TYPES = List.of(SourceKind.JOB, SourceKind.BUILD, SourceKind.QUEUE,
            SourceKind.NODE, SourceKind.FINGERPRINT, SourceKind.PLUGIN);
    private static final Set<String> REQUIRED = Set.of("jobs.json", "builds.json", "queues.json", "nodes.json",
            "fingerprints.json", "plugins.json", "errors.json", "capabilities.json", "analysis.json", "checkpoint.json");
    private final Path state;
    private final Path generations;
    private final AtomicLong identifiers = new AtomicLong();

    public GenerationStore(Path state) throws IOException {
        this.state = state.toAbsolutePath().normalize(); generations = this.state.resolve("generations");
        Files.createDirectories(generations); Files.createDirectories(this.state.resolve("leases"));
        identifiers.set(highestOrdinal());
    }

    public record Published(String generationId, GenerationManifest manifest, Snapshot snapshot) {}
    public record Verification(boolean valid, List<String> errors, GenerationManifest manifest) {}
    public record RecoverySelection(String generationId, Snapshot snapshot, List<String> diagnostics) {}
    public record RetentionResult(List<String> retained, List<String> deleted, List<String> leased) {}

    public synchronized Published publish(Snapshot source, Map<String, Object> analysis) throws IOException {
        String generationId = nextId(source.checkpoint().appliedSequence());
        String digest = stateDigest(source);
        Snapshot snapshot = withCheckpoint(source, new Checkpoint(source.checkpoint().appliedSequence(), generationId, digest));
        Path staging = generations.resolve("." + generationId + ".staging"); Path destination = generations.resolve(generationId);
        deleteTree(staging); Files.createDirectories(staging); Map<String, String> checksums = new TreeMap<>();
        try {
            for (SourceKind type : TYPES) writeChecked(staging, fileName(type), rows(snapshot, type), checksums);
            writeChecked(staging, "errors.json", snapshot.errors().stream().map(SourceError::toMap).toList(), checksums);
            writeChecked(staging, "capabilities.json", Domain.ordered("unsupportedSources",
                    snapshot.unsupportedSources().stream().map(Enum::name).sorted().toList()), checksums);
            writeChecked(staging, "analysis.json", analysis, checksums);
            writeChecked(staging, "checkpoint.json", snapshot.checkpoint().toMap(), checksums);
                String contentDigest = digest;
            GenerationManifest manifest = new GenerationManifest(CURRENT_SCHEMA, generationId, deterministicTimestamp(generationId),
                    0, snapshot.checkpoint().appliedSequence(), snapshot.recordCount(), checksums, contentDigest);
            Json.write(staging.resolve("manifest.json"), manifest.toMap()); force(staging.resolve("manifest.json"));
            Verification staged = verify(staging, generationId);
            if (!staged.valid()) throw new IOException("staged generation did not verify: " + staged.errors());
            move(staging, destination); forceDirectory(generations);
            Verification complete = verify(destination, generationId);
            if (!complete.valid()) throw new IOException("published generation did not verify: " + complete.errors());
            writeCurrent(generationId);
            return new Published(generationId, manifest, snapshot);
        } catch (IOException | RuntimeException failure) {
            deleteTree(staging); throw failure;
        }
    }

    public Optional<String> currentId() throws IOException {
        Path pointer = state.resolve("CURRENT"); if (!Files.isRegularFile(pointer)) return Optional.empty();
        String value = Files.readString(pointer, StandardCharsets.UTF_8).trim();
        return value.isBlank() ? Optional.empty() : Optional.of(value);
    }
    public Snapshot loadCurrent() throws IOException {
        String id = currentId().orElseThrow(() -> new IOException("CURRENT is absent"));
        Verification verification = verify(generations.resolve(id));
        if (!verification.valid()) throw new IOException("CURRENT is invalid: " + verification.errors());
        return load(generations.resolve(id));
    }
    public RecoverySelection recover() throws IOException {
        List<Path> candidates = listGenerations();
        if (candidates.isEmpty()) return new RecoverySelection("", Snapshot.empty(), List.of("no generation available"));
        RecoveryPlanner.Plan plan = new RecoveryPlanner().plan(candidates, currentId().orElse(""), this);
        Optional<RecoveryPlanner.Candidate> complete = new RecoveryPlanner().highestComplete(plan);
        if (complete.isEmpty()) {
            Optional<RecoveryPlanner.Candidate> legacy = plan.candidates().stream()
                .filter(candidate -> candidate.state() == RecoveryPlanner.CandidateState.LEGACY)
                .max(Comparator.comparingLong(RecoveryPlanner.Candidate::lastSequence)
                    .thenComparing(RecoveryPlanner.Candidate::generationId));
            if (legacy.isPresent()) { migrate(legacy.get().generationId()); return recover(); }
        }
        RecoveryPlanner.Candidate selected = complete
            .orElseThrow(() -> new IOException("no valid generation: " + plan.candidates()));
        writeCurrent(selected.generationId());
        return new RecoverySelection(selected.generationId(), load(selected.directory()), List.of(plan.reason()));
    }
    public Verification verifyCurrent() throws IOException {
        Optional<String> current = currentId();
        return current.isEmpty() ? new Verification(false, List.of("CURRENT is absent"), null)
                : verify(generations.resolve(current.get()));
    }
    public Verification verify(Path directory) throws IOException { return verify(directory, directory.getFileName().toString()); }

    private Verification verify(Path directory, String expectedId) throws IOException {
        List<String> errors = new ArrayList<>(); Path manifestPath = directory.resolve("manifest.json");
        if (!Files.isRegularFile(manifestPath)) return new Verification(false, List.of("manifest is absent"), null);
        GenerationManifest manifest;
        try { manifest = manifest(Json.object(manifestPath)); }
        catch (RuntimeException invalid) { return new Verification(false, List.of("manifest invalid: " + invalid.getMessage()), null); }
        if (manifest.schemaVersion() != CURRENT_SCHEMA) errors.add("unsupported schema version");
        if (!manifest.generationId().equals(expectedId)) errors.add("generation identifier mismatch");
        if (!manifest.checksums().keySet().equals(REQUIRED)) errors.add("manifest file set mismatch");
        for (Map.Entry<String, String> expected : manifest.checksums().entrySet()) {
            Path file = directory.resolve(expected.getKey());
            if (!Files.isRegularFile(file)) errors.add("missing " + expected.getKey());
            else if (!checksum(file).equals(expected.getValue())) errors.add("checksum mismatch " + expected.getKey());
        }
        if (manifest.firstSequence() > manifest.lastSequence()) errors.add("checkpoint bounds reversed");
        if (errors.isEmpty()) {
            try {
                Snapshot snapshot = load(directory);
                if (snapshot.recordCount() != manifest.recordCount()) errors.add("record count mismatch");
                if (snapshot.checkpoint().appliedSequence() != manifest.lastSequence()) errors.add("checkpoint sequence mismatch");
                if (!snapshot.checkpoint().generationId().equals(manifest.generationId())) errors.add("checkpoint generation mismatch");
                if (!snapshot.checkpoint().digest().equals(stateDigest(snapshot))) errors.add("checkpoint digest mismatch");
                if (!manifest.contentDigest().equals(stateDigest(snapshot))) errors.add("content digest mismatch");
                SnapshotAuditor.Audit audit = new SnapshotAuditor().audit(snapshot);
                if (!audit.valid()) errors.add("typed snapshot audit failed");
            } catch (RuntimeException | IOException invalid) { errors.add("typed content invalid: " + invalid.getMessage()); }
        }
        return new Verification(errors.isEmpty(), List.copyOf(errors), manifest);
    }

    public synchronized String migrate(String generationId) throws IOException {
        Path source = generations.resolve(generationId); GenerationManifest old = manifest(Json.object(source.resolve("manifest.json")));
        if (old.schemaVersion() >= CURRENT_SCHEMA) return generationId;
        String migrationId = nextId(old.lastSequence()); Path staging = generations.resolve("." + migrationId + ".migration");
        deleteTree(staging); copyTree(source, staging);
        try {
            new SchemaMigrator().migrate(staging, old.schemaVersion(), CURRENT_SCHEMA);
            Snapshot migrated = load(staging); Object analysis = Json.parse(staging.resolve("analysis.json"));
            deleteTree(staging); return publish(migrated, analysis instanceof Map<?, ?> map ? stringMap(map) : Map.of()).generationId();
        } finally { deleteTree(staging); }
    }

    public Lease lease(String generationId, String owner) throws IOException {
        if (!verify(generations.resolve(generationId)).valid()) throw new IOException("cannot lease invalid generation");
        Path lease = state.resolve("leases").resolve(generationId + "--" + sanitize(owner) + ".lease");
        Files.writeString(lease, generationId + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW);
        force(lease); return new Lease(lease);
    }
    public synchronized RetentionResult compact(int retain) throws IOException {
        if (retain < 1) throw new IllegalArgumentException("retain must be positive");
        List<Path> candidates = listGenerations(); Set<String> leasedIds = leasedIds();
        RetentionPlanner.Plan plan = new RetentionPlanner().plan(candidates, currentId().orElse(""), leasedIds,
                retain, new RetentionPlanner().readReferences(candidates));
        for (String id : plan.removable()) deleteTree(generations.resolve(id));
        return new RetentionResult(plan.retained(), plan.removable(), leasedIds.stream().sorted().toList());
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
                Map<String, Object> row = (Map<String, Object>) raw;
                CanonicalRecord record = RecordCodec.decode(type, row, RecordCodec.number(row, "sequence", 0));
                if (record instanceof JobRecord value) jobs.put(value.key(), value); else if (record instanceof BuildRecord value) builds.put(value.key(), value);
                else if (record instanceof QueueRecord value) queue.put(value.key(), value); else if (record instanceof NodeRecord value) nodes.put(value.key(), value);
                else if (record instanceof FingerprintRecord value) fingerprints.put(value.key(), value); else if (record instanceof PluginRecord value) plugins.put(value.key(), value);
            }
        }
        List<SourceError> errors = new ArrayList<>(); Object errorData = Json.parse(directory.resolve("errors.json"));
        if (!(errorData instanceof List<?> errorRows)) throw new IOException("errors file is not an array");
        for (Object item : errorRows) {
            if (!(item instanceof Map<?, ?> raw)) throw new IOException("error record is not an object");
            Map<String, Object> row = (Map<String, Object>) raw;
            errors.add(new SourceError(SourceKind.valueOf(RecordCodec.text(row, "source", "JOB")),
                    RecordCodec.text(row, "recordKey", ""), RecordCodec.text(row, "code", "UNKNOWN"), RecordCodec.text(row, "message", "")));
        }
        Set<SourceKind> unsupported = new java.util.LinkedHashSet<>(); Path capabilities = directory.resolve("capabilities.json");
        if (Files.isRegularFile(capabilities)) {
            Object raw = Json.object(capabilities).get("unsupportedSources");
            if (raw instanceof Collection<?> values) for (Object value : values) unsupported.add(SourceKind.valueOf(String.valueOf(value)));
        }
        Map<String, Object> checkpointData = Json.object(directory.resolve("checkpoint.json"));
        Checkpoint checkpoint = new Checkpoint(RecordCodec.number(checkpointData, "appliedSequence", 0),
                RecordCodec.text(checkpointData, "generationId", directory.getFileName().toString()),
                RecordCodec.text(checkpointData, "digest", ""));
        return new Snapshot(jobs, builds, queue, nodes, fingerprints, plugins, errors, unsupported, checkpoint);
    }

    private Snapshot withCheckpoint(Snapshot value, Checkpoint checkpoint) {
        return new Snapshot(value.jobs(), value.builds(), value.queue(), value.nodes(), value.fingerprints(),
                value.plugins(), value.errors(), value.unsupportedSources(), checkpoint);
    }
    private String stateDigest(Snapshot snapshot) {
        Map<String, Object> content = Domain.ordered("jobs", digestRows(snapshot, SourceKind.JOB),
                "builds", digestRows(snapshot, SourceKind.BUILD), "queue", digestRows(snapshot, SourceKind.QUEUE),
                "nodes", digestRows(snapshot, SourceKind.NODE), "fingerprints", digestRows(snapshot, SourceKind.FINGERPRINT),
                "plugins", digestRows(snapshot, SourceKind.PLUGIN),
                "errors", snapshot.errors().stream().map(SourceError::toMap).toList(),
                "unsupportedSources", snapshot.unsupportedSources().stream().map(Enum::name).sorted().toList());
        return CanonicalJson.document(content, snapshot.recordCount()).sha256();
    }
    private List<Map<String, Object>> digestRows(Snapshot snapshot, SourceKind type) {
        return rows(snapshot, type).stream().map(row -> {
            Map<String, Object> content = new LinkedHashMap<>(row); content.remove("sequence"); return content;
        }).toList();
    }
    private List<Map<String, Object>> rows(Snapshot snapshot, SourceKind type) {
        Collection<? extends CanonicalRecord> records = switch (type) {
            case JOB -> snapshot.jobs().values(); case BUILD -> snapshot.builds().values(); case QUEUE -> snapshot.queue().values();
            case NODE -> snapshot.nodes().values(); case FINGERPRINT -> snapshot.fingerprints().values(); case PLUGIN -> snapshot.plugins().values();
        };
        return records.stream().sorted(Comparator.comparing(CanonicalRecord::key)).map(CanonicalRecord::toMap).toList();
    }
    private void writeChecked(Path directory, String name, Object value, Map<String, String> checksums) throws IOException {
        Path file = directory.resolve(name); CanonicalJson.write(file, value); force(file); checksums.put(name, checksum(file));
    }
    private long highestOrdinal() throws IOException {
        long highest = 0;
        for (Path path : listGenerations()) {
            String[] parts = path.getFileName().toString().split("-");
            if (parts.length == 3) try { highest = Math.max(highest, Long.parseLong(parts[2])); } catch (NumberFormatException ignored) {}
        }
        return highest;
    }
    private String nextId(long sequence) { return String.format("gen-%012d-%04d", sequence, identifiers.incrementAndGet()); }
    private long deterministicTimestamp(String generationId) { return 1_735_689_600_000L + Integer.toUnsignedLong(generationId.hashCode()); }
    private String fileName(SourceKind kind) { return kind.name().toLowerCase() + "s.json"; }
    private String checksum(Path path) throws IOException { return Domain.sha256(Files.readString(path, StandardCharsets.UTF_8)); }
    private void writeCurrent(String id) throws IOException {
        Path temporary = state.resolve("CURRENT.tmp"); Files.writeString(temporary, id + "\n", StandardCharsets.UTF_8);
        force(temporary); move(temporary, state.resolve("CURRENT")); forceDirectory(state);
    }
    private void move(Path from, Path to) throws IOException {
        try { Files.move(from, to, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
        catch (AtomicMoveNotSupportedException unsupported) { throw new IOException("atomic move is required", unsupported); }
    }
    private void force(Path path) throws IOException { try (FileChannel channel = FileChannel.open(path, StandardOpenOption.WRITE)) { channel.force(true); } }
    private void forceDirectory(Path path) { try (FileChannel channel = FileChannel.open(path, StandardOpenOption.READ)) { channel.force(true); } catch (IOException ignored) {} }
    private List<Path> listGenerations() throws IOException {
        List<Path> result = new ArrayList<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(generations, "gen-*")) { for (Path path : stream) if (Files.isDirectory(path)) result.add(path); }
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
    private void copyTree(Path from, Path to) throws IOException {
        try (var paths = Files.walk(from)) { for (Path source : paths.toList()) {
            Path destination = to.resolve(from.relativize(source));
            if (Files.isDirectory(source)) Files.createDirectories(destination); else Files.copy(source, destination, StandardCopyOption.REPLACE_EXISTING);
        }}
    }
    private void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        try (var paths = Files.walk(root)) { for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(path); }
    }
    private Map<String, Object> stringMap(Map<?, ?> source) {
        Map<String, Object> result = new LinkedHashMap<>(); source.forEach((key, value) -> result.put(String.valueOf(key), value)); return result;
    }
    public static final class Lease implements AutoCloseable {
        private final Path path; private Lease(Path path) { this.path = path; }
        public Path path() { return path; }
        @Override public void close() throws IOException { Files.deleteIfExists(path); }
    }
}