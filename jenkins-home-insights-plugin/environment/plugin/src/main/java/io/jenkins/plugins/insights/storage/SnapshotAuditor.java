package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.json.CanonicalJson;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.BuildRecord;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.FingerprintRecord;
import io.jenkins.plugins.insights.model.Domain.JobRecord;
import io.jenkins.plugins.insights.model.Domain.NodeRecord;
import io.jenkins.plugins.insights.model.Domain.PluginRecord;
import io.jenkins.plugins.insights.model.Domain.QueueRecord;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Audits canonical state independently from filesystem generation checks. */
public final class SnapshotAuditor {
    public enum Severity { INFO, WARNING, ERROR }
    public record Finding(Severity severity, String code, SourceKind source, String recordKey, String detail) {
        public Map<String, Object> toMap() {
            return Domain.ordered("severity", severity.name(), "code", code,
                    "source", source == null ? null : source.name(), "recordKey", recordKey, "detail", detail);
        }
    }
    public record Audit(int records, Map<SourceKind, Integer> counts, List<Finding> findings,
                        String canonicalDigest, boolean valid) {
        public Map<String, Object> toMap() {
            Map<String, Integer> named = new TreeMap<>(); counts.forEach((key, value) -> named.put(key.name(), value));
            return Domain.ordered("records", records, "counts", named,
                    "findings", findings.stream().map(Finding::toMap).toList(),
                    "canonicalDigest", canonicalDigest, "valid", valid);
        }
    }

    public Audit audit(Snapshot snapshot) {
        List<Finding> findings = new ArrayList<>(); Map<SourceKind, Integer> counts = new EnumMap<>(SourceKind.class);
        Set<String> global = new HashSet<>();
        for (CanonicalRecord record : snapshot.allRecords()) {
            counts.merge(record.kind(), 1, Integer::sum); String compound = record.kind().name() + ":" + record.key();
            if (!global.add(compound)) findings.add(error("DUPLICATE_KEY", record, "canonical key appears more than once"));
            if (record.key().isBlank()) findings.add(error("EMPTY_KEY", record, "canonical key is empty"));
            if (record.observedSequence() < 0) findings.add(error("NEGATIVE_SEQUENCE", record, "observed sequence is negative"));
        }
        auditJobs(snapshot, findings); auditBuilds(snapshot, findings); auditQueue(snapshot, findings);
        auditNodes(snapshot, findings); auditFingerprints(snapshot, findings); auditPlugins(snapshot, findings);
        if (snapshot.checkpoint().appliedSequence() < maximumSequence(snapshot.allRecords())) {
            findings.add(new Finding(Severity.ERROR, "CHECKPOINT_BEHIND_RECORDS", null, "",
                    "checkpoint does not cover every represented record"));
        }
        String digest = CanonicalJson.snapshot(snapshot).sha256();
        boolean valid = findings.stream().noneMatch(finding -> finding.severity() == Severity.ERROR);
        return new Audit(snapshot.recordCount(), Map.copyOf(counts), List.copyOf(findings), digest, valid);
    }

    private void auditJobs(Snapshot snapshot, List<Finding> findings) {
        Map<String, String> fullNames = new HashMap<>();
        for (JobRecord job : snapshot.jobs().values()) {
            String previous = fullNames.putIfAbsent(job.fullName(), job.key());
            if (previous != null && !previous.equals(job.key())) findings.add(error("DUPLICATE_FULL_NAME", job, "full name maps to multiple keys"));
            if (!job.url().isBlank() && !job.url().startsWith("/")) findings.add(warning("NON_LOCAL_URL", job, "job URL is not controller relative"));
            if (job.labels().stream().anyMatch(String::isBlank)) findings.add(error("EMPTY_LABEL", job, "job has an empty label atom"));
        }
    }

    private void auditBuilds(Snapshot snapshot, List<Finding> findings) {
        Map<String, Set<Long>> numbers = new HashMap<>();
        for (BuildRecord build : snapshot.builds().values()) {
            if (!snapshot.jobs().containsKey(build.jobKey())) findings.add(warning("MISSING_JOB", build, "owning job is not retained"));
            if (build.number() < 1) findings.add(error("INVALID_BUILD_NUMBER", build, "build number must be positive"));
            if (build.startedMillis() < 0 || build.durationMillis() < 0) findings.add(error("INVALID_BUILD_TIME", build, "build time is negative"));
            if (!numbers.computeIfAbsent(build.jobKey(), ignored -> new HashSet<>()).add(build.number()))
                findings.add(error("DUPLICATE_BUILD_NUMBER", build, "job has duplicate build number"));
        }
    }

    private void auditQueue(Snapshot snapshot, List<Finding> findings) {
        for (QueueRecord item : snapshot.queue().values()) {
            if (!snapshot.jobs().containsKey(item.taskKey())) findings.add(warning("MISSING_QUEUE_TASK", item, "queue task is not retained"));
            if (item.enqueuedMillis() < 0) findings.add(error("INVALID_QUEUE_TIME", item, "queue timestamp is negative"));
            if (item.labels().stream().anyMatch(String::isBlank)) findings.add(error("EMPTY_QUEUE_LABEL", item, "queue item has an empty label atom"));
        }
    }

    private void auditNodes(Snapshot snapshot, List<Finding> findings) {
        for (NodeRecord node : snapshot.nodes().values()) {
            if (node.busyExecutors() > node.executors()) findings.add(error("BUSY_EXCEEDS_TOTAL", node, "busy executor count exceeds total"));
            if (!node.online() && node.availableExecutors() != 0) findings.add(error("OFFLINE_CAPACITY", node, "offline node exposes capacity"));
            if (!node.acceptingTasks() && node.availableExecutors() != 0) findings.add(error("REFUSING_CAPACITY", node, "non-accepting node exposes capacity"));
        }
    }

    private void auditFingerprints(Snapshot snapshot, List<Finding> findings) {
        for (FingerprintRecord fingerprint : snapshot.fingerprints().values()) {
            boolean producerPresent = snapshot.builds().containsKey(fingerprint.producerBuildKey());
            if (producerPresent && fingerprint.producerMissing()) findings.add(warning("STALE_MISSING_MARKER", fingerprint, "producer exists but is marked missing"));
            if (!producerPresent && !fingerprint.producerMissing()) findings.add(warning("UNMARKED_MISSING_PRODUCER", fingerprint, "producer is absent without marker"));
            if (fingerprint.consumerBuildKeys().contains(fingerprint.producerBuildKey())) findings.add(warning("SELF_LINEAGE", fingerprint, "producer also consumes its artifact"));
        }
    }

    private void auditPlugins(Snapshot snapshot, List<Finding> findings) {
        Map<String, String> names = new HashMap<>();
        for (PluginRecord plugin : snapshot.plugins().values()) {
            String previous = names.putIfAbsent(plugin.shortName(), plugin.key());
            if (previous != null && !previous.equals(plugin.key())) findings.add(error("DUPLICATE_PLUGIN", plugin, "short name maps to multiple records"));
            if (plugin.active() && !plugin.enabled()) findings.add(warning("ACTIVE_DISABLED", plugin, "disabled plugin is active"));
            if (plugin.version().isBlank()) findings.add(warning("MISSING_PLUGIN_VERSION", plugin, "plugin version is absent"));
        }
    }

    private long maximumSequence(Collection<CanonicalRecord> records) { return records.stream().mapToLong(CanonicalRecord::observedSequence).max().orElse(0); }
    private Finding error(String code, CanonicalRecord record, String detail) { return new Finding(Severity.ERROR, code, record.kind(), record.key(), detail); }
    private Finding warning(String code, CanonicalRecord record, String detail) { return new Finding(Severity.WARNING, code, record.kind(), record.key(), detail); }
}
