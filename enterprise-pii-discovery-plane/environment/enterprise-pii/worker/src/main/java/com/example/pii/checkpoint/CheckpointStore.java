package com.example.pii.checkpoint;

import com.example.pii.protocol.Protocol;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

public final class CheckpointStore {
    private final Path directory;

    public CheckpointStore(Path directory) throws IOException {
        this.directory = directory;
        Files.createDirectories(directory);
    }

    public record Checkpoint(
            String jobId,
            String shardId,
            long generation,
            int attempt,
            String policyDigest,
            long sequence,
            String sourceIdentity,
            String readerCheckpoint,
            Instant committedAt) {}

    public void save(Checkpoint checkpoint) throws IOException {
        Path target = path(checkpoint.jobId(), checkpoint.shardId());
        Path temporary = target.resolveSibling(target.getFileName() + ".tmp");
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("attempt", checkpoint.attempt());
        value.put("committed_at", checkpoint.committedAt());
        value.put("generation", checkpoint.generation());
        value.put("job_id", checkpoint.jobId());
        value.put("policy_digest", checkpoint.policyDigest());
        value.put("reader_checkpoint", checkpoint.readerCheckpoint());
        value.put("sequence", checkpoint.sequence());
        value.put("shard_id", checkpoint.shardId());
        value.put("source_identity", checkpoint.sourceIdentity());
        String body = Protocol.canonicalJson(value);
        Files.writeString(temporary, body + "\n", StandardCharsets.UTF_8);
        Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
    }

    public String raw(String jobId, String shardId) throws IOException {
        Path path = path(jobId, shardId);
        return Files.exists(path) ? Files.readString(path, StandardCharsets.UTF_8).strip() : "";
    }

    public void clear(String jobId, String shardId) throws IOException {
        Files.deleteIfExists(path(jobId, shardId));
    }

    private Path path(String jobId, String shardId) {
        return directory.resolve(safe(jobId) + "--" + safe(shardId) + ".json");
    }

    private String safe(String value) {
        if (!value.matches("[A-Za-z0-9_.:-]+")) throw new IllegalArgumentException("unsafe checkpoint identity");
        return value.replace(':', '_');
    }
}