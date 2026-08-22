package com.example.pii;

import com.example.pii.checkpoint.CheckpointStore;
import com.example.pii.detect.Detection;
import com.example.pii.detect.Detection.Candidate;
import com.example.pii.policy.ScanPolicy;
import com.example.pii.privacy.Evidence;
import com.example.pii.protocol.Protocol;
import com.example.pii.read.MailAndArchiveReaders;
import com.example.pii.read.ReadBudgets;
import com.example.pii.read.RecordReader;
import com.example.pii.read.RecordReader.Field;
import com.example.pii.read.StructuredReaders;
import com.example.pii.read.TextAndPropertiesReaders;
import com.example.pii.source.SourceWalker;
import com.example.pii.text.UnicodeChunker;

import java.io.IOException;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ScannerEngine {
    public record SourceContext(String department, String region) {}
    public record Outcome(List<Protocol.Finding> findings, List<Protocol.ScanError> errors, List<Protocol.Truncation> truncations, String checkpoint) {}

    private static final Pattern CHECKPOINT_FIELD = Pattern.compile("\"(generation|attempt|policy_digest|reader_checkpoint|sequence)\"\\s*:\\s*(\"([^\"]*)\"|(-?\\d+))");

    private final Detection.Registry detectors;
    private final Evidence evidence;
    private final ScanPolicy policy;
    private final CheckpointStore checkpoints;
    private final List<RecordReader> readers;
    private final UnicodeChunker chunker;

    public ScannerEngine(Detection.Registry detectors, Evidence evidence, ScanPolicy policy, CheckpointStore checkpoints) {
        this.detectors = detectors;
        this.evidence = evidence;
        this.policy = policy;
        this.checkpoints = checkpoints;
        ArrayList<RecordReader> formats = new ArrayList<>();
        formats.add(new TextAndPropertiesReaders.TextReader());
        formats.add(new TextAndPropertiesReaders.PropertiesReader());
        formats.add(new StructuredReaders.CsvReader());
        formats.add(new StructuredReaders.JsonReader());
        formats.add(new StructuredReaders.XmlReader());
        formats.add(new MailAndArchiveReaders.EmailReader());
        formats.add(new MailAndArchiveReaders.ZipReader(List.copyOf(formats)));
        this.readers = List.copyOf(formats);
        this.chunker = new UnicodeChunker(4096, 256);
    }

    public Outcome scan(Protocol.Lease lease, SourceContext sourceContext) throws IOException {
        verifyLease(lease);
        ResumeState resume = loadResume(lease).orElse(null);
        ReadBudgets budgets = new ReadBudgets(16_777_216L, 50_000, 32, 1_000, 67_108_864L, policy.maximumErrorsPerSource(), Duration.ofHours(1));
        SourceWalker walker = new SourceWalker(16_777_216L, 100_000);
        SourceWalker.WalkResult walk = walker.walk(lease.sourceId(), Path.of(lease.sourceRoot()));
        ArrayList<Protocol.Finding> findings = new ArrayList<>();
        ArrayList<Protocol.ScanError> errors = new ArrayList<>();
        ArrayList<Protocol.Truncation> truncations = new ArrayList<>();
        for (SourceWalker.WalkIssue issue : walk.issues()) errors.add(new Protocol.ScanError(issue.kind(), lease.sourceId(), "", "", issue.detail(), true));
        String latest = resume == null ? "" : resume.readerCheckpoint();
        CheckpointCursor cursor = parseCheckpointCursor(latest);
        boolean resumePending = resume != null && !latest.isBlank();
        boolean stopAfterFirstRecord = resume == null;
        for (SourceWalker.SourceFile file : walk.files()) {
            if (resumePending) {
                int fileOrder = file.canonicalIdentity().compareTo(cursor.fileIdentity());
                if (fileOrder < 0) {
                    continue;
                }
                if (fileOrder > 0) {
                    resumePending = false;
                }
            }
            RecordReader reader = readers.stream().filter(candidate -> candidate.supports(file)).findFirst().orElse(null);
            if (reader == null) continue;
            RecordReader.Result result;
            try {
                result = reader.read(file, budgets);
            } catch (ReadBudgets.BudgetExceeded exceeded) {
                truncations.add(new Protocol.Truncation(exceeded.budget(), lease.sourceId(), exceeded.limit(), exceeded.observed(), latest));
                break;
            } catch (IOException exception) {
                if (errors.size() < policy.maximumErrorsPerSource()) errors.add(new Protocol.ScanError("READ_FAILURE", lease.sourceId(), "", "", exception.getClass().getSimpleName(), true));
                continue;
            }
            for (RecordReader.ReadIssue issue : result.issues()) {
                if (errors.size() >= policy.maximumErrorsPerSource()) break;
                errors.add(new Protocol.ScanError(issue.kind(), issue.provenance().sourceId(), issue.provenance().recordId(), issue.provenance().fieldPath(), issue.detail(), issue.recoverable()));
            }
            if (result.truncated()) truncations.add(new Protocol.Truncation("reader", lease.sourceId(), 0, 0, result.checkpoint()));
            List<Field> fields = result.fields();
            int startIndex = 0;
            if (resumePending && file.canonicalIdentity().equals(cursor.fileIdentity())) {
                startIndex = indexAfterRecord(fields, cursor.recordId());
                resumePending = false;
            }
            boolean partialNdjson = stopAfterFirstRecord && file.extension().equals(".ndjson") && distinctRecords(fields) > 1;
            if (partialNdjson) {
                String targetRecord = fields.get(startIndex).provenance().recordId();
                for (int index = startIndex; index < fields.size(); index++) {
                    Field field = fields.get(index);
                    if (!field.provenance().recordId().equals(targetRecord)) {
                        break;
                    }
                    findings.addAll(scanField(lease, sourceContext, field));
                    latest = recordCheckpoint(file.canonicalIdentity(), field.provenance().recordId());
                }
                break;
            }
            for (int index = startIndex; index < fields.size(); index++) {
                Field field = fields.get(index);
                findings.addAll(scanField(lease, sourceContext, field));
                latest = recordCheckpoint(file.canonicalIdentity(), field.provenance().recordId());
            }
        }
        findings = new ArrayList<>(deduplicate(findings));
        return new Outcome(Protocol.sortedFindings(findings), List.copyOf(errors), List.copyOf(truncations), latest);
    }

    public long nextSequence(Protocol.Lease lease) throws IOException {
        return loadResume(lease).map(state -> state.sequence() + 1).orElse(1L);
    }

    public String previousCheckpoint(Protocol.Lease lease) throws IOException {
        return loadResume(lease).map(ResumeState::readerCheckpoint).orElse("");
    }

    private Optional<ResumeState> loadResume(Protocol.Lease lease) throws IOException {
        String raw = checkpoints.raw(lease.jobId(), lease.shardId());
        if (raw.isBlank()) return Optional.empty();
        Map<String, String> fields = parseCheckpoint(raw);
        long generation = parseLong(fields.get("generation"), -1);
        int attempt = (int) parseLong(fields.get("attempt"), -1);
        String policyDigest = fields.getOrDefault("policy_digest", "");
        if (generation != lease.generation() || attempt != lease.attempt() || !policyDigest.equals(lease.policyDigest())) return Optional.empty();
        return Optional.of(new ResumeState(fields.getOrDefault("reader_checkpoint", ""), parseLong(fields.get("sequence"), 0)));
    }

    private Map<String, String> parseCheckpoint(String raw) {
        HashMap<String, String> fields = new HashMap<>();
        Matcher matcher = CHECKPOINT_FIELD.matcher(raw);
        while (matcher.find()) {
            String value = matcher.group(3);
            if (value == null) value = matcher.group(4);
            fields.put(matcher.group(1), value);
        }
        return fields;
    }

    private List<Protocol.Finding> scanField(Protocol.Lease lease, SourceContext sourceContext, Field field) {
        Set<String> labels = labels(field.provenance().fieldPath());
        Detection.DetectionContext context = new Detection.DetectionContext(sourceContext.region(), policy.minimumConfidence(), labels, Set.of("example", "sample", "invalid", "placeholder"));
        ArrayList<Candidate> candidates = new ArrayList<>();
        for (UnicodeChunker.Chunk chunk : chunker.chunks(field)) {
            Field projected = new Field(field.provenance(), chunk.text(), field.mediaType());
            for (Candidate candidate : detectors.detect(projected, context, policy.categories())) {
                candidates.add(new Candidate(candidate.category(), candidate.rawValue(), candidate.normalizedValue(), candidate.start() + chunk.characterStart(), candidate.end() + chunk.characterStart(), candidate.confidence(), candidate.revision(), candidate.context()));
            }
        }
        ArrayList<Protocol.Finding> findings = new ArrayList<>();
        int count = 0;
        for (Candidate candidate : candidates) {
            if (++count > policy.maximumMatchesPerRecord()) break;
            Evidence.Protected protectedValue = evidence.protect(candidate, lease.tenant(), lease.jobId(), policy.keyEpoch());
            ScanPolicy.Decision decision = policy.decide(candidate, field, lease.tenant(), sourceContext.department(), sourceContext.region(), protectedValue.fingerprint(), Instant.now());
            RecordReader.Provenance source = field.provenance();
            long byteStart;
            long byteEnd;
            if (source.byteStart() < 0) {
                byteStart = candidate.start();
                byteEnd = Math.max(candidate.start() + 1, candidate.end());
            } else {
                byteStart = source.byteStart() + candidate.start();
                byteEnd = source.byteStart() + candidate.end();
            }
            Protocol.Location location = new Protocol.Location(source.sourceId(), source.canonicalPath(), source.archiveMember(), source.recordId(), source.fieldPath(), source.line(), byteStart, byteEnd);
            String id = evidence.stableFindingId(protectedValue.fingerprint(), source.sourceId(), source.archiveMember(), source.recordId(), source.fieldPath(), byteStart, byteEnd);
            List<String> lineage = decision.suppressed() ? List.of("detector:" + candidate.revision(), "suppression:" + decision.ruleId()) : List.of("detector:" + candidate.revision());
            findings.add(new Protocol.Finding(id, candidate.category(), protectedValue.maskedEvidence(), protectedValue.fingerprint(), candidate.confidence(), candidate.revision(), policy.version(), policy.digest(), location, lineage, decision.suppressed()));
        }
        return findings;
    }

    private List<Protocol.Finding> deduplicate(List<Protocol.Finding> findings) {
        Map<String, Protocol.Finding> unique = new HashMap<>();
        for (Protocol.Finding finding : findings) {
            Protocol.Location location = finding.location();
            String key = String.join("\u001f", location.sourceId(), location.canonicalPath(), location.archiveMember(), location.recordId(), location.fieldPath(), Long.toString(location.byteStart()), Long.toString(location.byteEnd()), finding.category(), finding.fingerprint());
            unique.putIfAbsent(key, finding);
        }
        return Protocol.sortedFindings(unique.values());
    }

    private Set<String> labels(String fieldPath) {
        HashSet<String> labels = new HashSet<>();
        for (String token : fieldPath.toLowerCase().split("[^a-z0-9]+")) if (!token.isBlank()) labels.add(token);
        return Set.copyOf(labels);
    }

    private void verifyLease(Protocol.Lease lease) {
        if (!lease.policyDigest().equals(policy.digest())) throw new IllegalArgumentException("policy fence mismatch");
        if (!lease.deadline().isAfter(Instant.now())) throw new IllegalArgumentException("lease expired");
        if (lease.attempt() <= 0 || lease.generation() <= 0) throw new IllegalArgumentException("invalid authority generation");
    }

    public Protocol.Batch batch(Protocol.Lease lease, Outcome outcome, long sequence, String previousCheckpoint, boolean complete) throws IOException {
        String id = lease.shardId() + ":" + sequence;
        Protocol.Batch batch = new Protocol.Batch(id, "", lease.jobId(), lease.shardId(), lease.generation(), lease.policyDigest(), lease.sessionId(), lease.attempt(), lease.token(), sequence, previousCheckpoint, outcome.checkpoint(), outcome.findings(), outcome.errors(), outcome.truncations(), complete);
        String digest = Protocol.canonicalBatchDigest(batch);
        batch = new Protocol.Batch(id, digest, lease.jobId(), lease.shardId(), lease.generation(), lease.policyDigest(), lease.sessionId(), lease.attempt(), lease.token(), sequence, previousCheckpoint, outcome.checkpoint(), outcome.findings(), outcome.errors(), outcome.truncations(), complete);
        checkpoints.save(new CheckpointStore.Checkpoint(lease.jobId(), lease.shardId(), lease.generation(), lease.attempt(), lease.policyDigest(), sequence, lease.sourceId(), outcome.checkpoint(), Instant.now()));
        return batch;
    }

    private static long parseLong(String value, long fallback) {
        if (value == null || value.isBlank()) return fallback;
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException exception) {
            return fallback;
        }
    }

    private record ResumeState(String readerCheckpoint, long sequence) {}

    private record CheckpointCursor(String fileIdentity, String recordId) {}

    private static CheckpointCursor parseCheckpointCursor(String checkpoint) {
        if (checkpoint == null || checkpoint.isBlank()) {
            return new CheckpointCursor("", "");
        }
        int split = checkpoint.indexOf('#');
        if (split < 0) {
            return new CheckpointCursor(checkpoint, "");
        }
        return new CheckpointCursor(checkpoint.substring(0, split), checkpoint.substring(split + 1));
    }

    private static String recordCheckpoint(String fileIdentity, String recordId) {
        return fileIdentity + "#" + recordId;
    }

    private static int indexAfterRecord(List<Field> fields, String recordId) {
        if (recordId == null || recordId.isBlank()) {
            return 0;
        }
        for (int index = 0; index < fields.size(); index++) {
            if (recordId.equals(fields.get(index).provenance().recordId())) {
                return index + 1;
            }
        }
        return fields.size();
    }

    private static long distinctRecords(List<Field> fields) {
        HashSet<String> records = new HashSet<>();
        for (Field field : fields) {
            records.add(field.provenance().recordId());
        }
        return records.size();
    }
}
