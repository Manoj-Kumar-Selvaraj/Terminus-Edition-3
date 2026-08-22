package io.jenkins.plugins.insights.generator;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/** Materializes a deterministic sanitized controller export without secrets. */
public final class HomeGenerator {
    public static final long DEFAULT_SEED = 731927L;
    public static final int DEFAULT_RECORDS = 14_536;
    private static final long BASE_TIME = 1_735_689_600_000L;

    public record GenerationSummary(int jobs, int builds, int queue, int nodes, int fingerprints,
                                    int plugins, int malformed, String digest) {
        public int total() { return jobs + builds + queue + nodes + fingerprints + plugins; }
        public Map<String, Object> toMap() {
            return Domain.ordered("jobs", jobs, "builds", builds, "queue", queue, "nodes", nodes,
                    "fingerprints", fingerprints, "plugins", plugins, "malformed", malformed,
                    "total", total(), "digest", digest);
        }
    }

    public GenerationSummary generate(Path home, int requestedRecords, long seed) throws IOException {
        if (requestedRecords < 10_000 || requestedRecords > 20_000) throw new IllegalArgumentException("records must be between 10000 and 20000");
        Path export = home.resolve("exports"); Files.createDirectories(export);
        int jobs = Math.max(240, requestedRecords * 360 / DEFAULT_RECORDS);
        int nodes = Math.max(48, requestedRecords * 96 / DEFAULT_RECORDS);
        int plugins = Math.max(120, requestedRecords * 180 / DEFAULT_RECORDS);
        int queue = Math.max(500, requestedRecords * 900 / DEFAULT_RECORDS);
        int fingerprints = Math.max(1200, requestedRecords * 2200 / DEFAULT_RECORDS);
        int builds = requestedRecords - jobs - nodes - plugins - queue - fingerprints;
        SplittableRandom random = new SplittableRandom(seed);
        List<String> jobKeys = writeJobs(export.resolve("jobs.ndjson"), jobs, random.split());
        List<String> buildKeys = writeBuilds(export.resolve("builds.ndjson"), builds, jobKeys, random.split());
        writeQueue(export.resolve("queue.ndjson"), queue, jobKeys, random.split());
        writeNodes(export.resolve("nodes.ndjson"), nodes, random.split());
        writeFingerprints(export.resolve("fingerprints.ndjson"), fingerprints, buildKeys, random.split());
        writePlugins(export.resolve("plugins.ndjson"), plugins, random.split());
        Json.write(export.resolve("fingerprint-capability.json"), Domain.ordered("enumeration", true, "provider", "file-index-v1"));
        int malformed = injectSparseMalformed(export);
        String digest = digest(export);
        GenerationSummary summary = new GenerationSummary(jobs, builds, queue, nodes, fingerprints, plugins, malformed, digest);
        Json.write(export.resolve("inventory.json"), summary.toMap());
        Json.write(home.resolve("config.json"), Domain.ordered("format", "sanitized-jenkins-home-v1", "seed", seed,
                "baseTimeMillis", BASE_TIME, "recordCount", summary.total(), "secrets", false));
        return summary;
    }

    private List<String> writeJobs(Path path, int count, SplittableRandom random) throws IOException {
        String[] teams = {"payments", "search", "identity", "fulfillment", "risk", "platform", "analytics", "mobile"};
        String[] services = {"api", "worker", "release", "integration", "smoke", "migration", "nightly", "deploy"};
        String[] labels = {"linux", "windows", "arm64", "docker", "jdk17", "jdk21", "high-memory", "trusted"};
        List<String> keys = new ArrayList<>(count);
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                String team = teams[index % teams.length]; String service = services[(index / teams.length) % services.length];
                String fullName = team + "/" + service + "-" + (index / 64);
                String authorityId = "job-" + String.format("%05d", index); keys.add(authorityId);
                writeRow(writer, Domain.ordered("id", authorityId, "fullName", fullName,
                        "displayName", service + " " + (index / 64), "url", "/job/" + team + "/job/" + service + "-" + (index / 64) + "/",
                        "buildable", index % 17 != 0, "labels", List.of(labels[index % labels.length], labels[(index + 3) % labels.length]),
                        "state", index % 89 == 0 ? "DELETED" : "ACTIVE"));
            }
        }
        return keys;
    }

    private List<String> writeBuilds(Path path, int count, List<String> jobs, SplittableRandom random) throws IOException {
        String[] results = {"SUCCESS", "SUCCESS", "SUCCESS", "UNSTABLE", "FAILURE", "ABORTED", "NOT_BUILT"};
        List<String> keys = new ArrayList<>(count);
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                String job = jobs.get(index % jobs.size()); long number = index / jobs.size() + 1L; String key = job + "#" + number; keys.add(key);
                String result = index % 173 == 0 ? "RUNNING" : results[index % results.length];
                long started = BASE_TIME - (long) index * 83_000L; long duration = result.equals("RUNNING") ? 0 : 20_000 + random.nextInt(900_000);
                List<String> artifacts = index % 5 == 0 ? List.of("artifact-" + index, "report-" + (index % 97)) : List.of();
                writeRow(writer, Domain.ordered("id", key, "jobKey", job, "number", number, "displayName", "#" + number,
                        "startedMillis", started, "durationMillis", duration, "result", result,
                        "state", result.equals("RUNNING") ? "RUNNING" : "ACTIVE", "artifacts", artifacts));
            }
        }
        return keys;
    }

    private void writeQueue(Path path, int count, List<String> jobs, SplittableRandom random) throws IOException {
        String[][] labels = {{"linux"}, {"windows"}, {"linux", "docker"}, {"arm64", "jdk21"}, {"trusted", "high-memory"}};
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                boolean cancelled = index % 37 == 0;
                writeRow(writer, Domain.ordered("id", 50_000L + index, "taskKey", jobs.get((index * 7) % jobs.size()),
                        "labels", List.of(labels[index % labels.length]), "enqueuedMillis", BASE_TIME - random.nextInt(3_600_000),
                        "cancelled", cancelled, "blockageReason", cancelled ? "cancelled by user" : index % 9 == 0 ? "waiting for executor" : ""));
            }
        }
    }

    private void writeNodes(Path path, int count, SplittableRandom random) throws IOException {
        String[] primary = {"linux", "windows", "arm64", "docker", "trusted", "high-memory"};
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                int executors = 1 + index % 8; boolean online = index % 13 != 0; boolean accepting = index % 17 != 0;
                writeRow(writer, Domain.ordered("id", "node-" + String.format("%03d", index), "name", "agent-" + String.format("%03d", index),
                        "labels", List.of(primary[index % primary.length], index % 3 == 0 ? "jdk21" : "jdk17"),
                        "mode", index % 11 == 0 ? "EXCLUSIVE" : "NORMAL", "executors", executors,
                        "busyExecutors", random.nextInt(executors + 1), "online", online, "acceptingTasks", accepting));
            }
        }
    }

    private void writeFingerprints(Path path, int count, List<String> builds, SplittableRandom random) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                String producer = index % 101 == 0 ? "" : builds.get((index * 5) % builds.size());
                int consumers = 1 + index % 4; List<String> consumerKeys = new ArrayList<>();
                for (int offset = 0; offset < consumers; offset++) consumerKeys.add(builds.get((index * 11 + offset * 19) % builds.size()));
                String hash = Domain.sha256("fingerprint:" + index + ":" + random.nextLong());
                writeRow(writer, Domain.ordered("id", "fp-" + index, "hash", hash, "producerBuildKey", producer,
                        "consumerBuildKeys", consumerKeys, "producerMissing", producer.isBlank()));
            }
        }
    }

    private void writePlugins(Path path, int count, SplittableRandom random) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
            for (int index = 0; index < count; index++) {
                boolean enabled = index % 19 != 0; boolean active = enabled && index % 43 != 0;
                List<String> missing = index % 47 == 0 ? List.of("dependency-" + index % 13) : List.of();
                writeRow(writer, Domain.ordered("id", "plugin-" + index, "shortName", "plugin-" + String.format("%03d", index),
                        "displayName", "Operational Plugin " + index, "version", (1 + index % 5) + "." + (index % 17) + "." + random.nextInt(10),
                        "enabled", enabled, "active", active, "bundled", index % 23 == 0,
                        "compatible", index % 41 != 0, "restartPending", index % 29 == 0, "missingDependencies", missing));
            }
        }
    }

    private int injectSparseMalformed(Path export) throws IOException {
        Path builds = export.resolve("builds.ndjson");
        Files.writeString(builds, "{\"id\":\"malformed-build\",\"jobKey\":\"job-00017\",\"number\":\"not-a-number\",\"result\":\"SUCCESS\"}\n",
                StandardCharsets.UTF_8, java.nio.file.StandardOpenOption.APPEND);
        Path nodes = export.resolve("nodes.ndjson");
        Files.writeString(nodes, "{\"id\":\"broken-node\",\"name\":\"broken\",\"labels\":[],\"executors\":-2,\"busyExecutors\":0}\n",
                StandardCharsets.UTF_8, java.nio.file.StandardOpenOption.APPEND);
        return 2;
    }

    private String digest(Path export) throws IOException {
        StringBuilder content = new StringBuilder();
        try (var paths = Files.list(export)) {
            for (Path path : paths.sorted().toList()) content.append(path.getFileName()).append(':').append(Files.readString(path, StandardCharsets.UTF_8));
        }
        return Domain.sha256(content.toString());
    }

    private void writeRow(BufferedWriter writer, Map<String, Object> row) throws IOException {
        writer.write(Json.write(row)); writer.newLine();
    }
}