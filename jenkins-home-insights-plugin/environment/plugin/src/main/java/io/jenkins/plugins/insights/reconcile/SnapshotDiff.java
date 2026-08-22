package io.jenkins.plugins.insights.reconcile;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Computes deterministic generation changes for audit and incremental planning. */
public final class SnapshotDiff {
    public enum ChangeType { ADDED, UPDATED, DELETED, UNCHANGED }
    public record Change(SourceKind source, String key, ChangeType type, String beforeDigest,
                         String afterDigest, long beforeSequence, long afterSequence) {
        public Map<String, Object> toMap() {
            return Domain.ordered("source", source.name(), "key", key, "type", type.name(),
                    "beforeDigest", beforeDigest, "afterDigest", afterDigest,
                    "beforeSequence", beforeSequence, "afterSequence", afterSequence);
        }
    }
    public record Diff(List<Change> changes, Map<SourceKind, Integer> added,
                       Map<SourceKind, Integer> updated, Map<SourceKind, Integer> deleted,
                       String digest) {
        public boolean empty() { return changes.stream().allMatch(change -> change.type() == ChangeType.UNCHANGED); }
        public Map<String, Object> toMap() {
            return Domain.ordered("changes", changes.stream().map(Change::toMap).toList(),
                    "added", names(added), "updated", names(updated), "deleted", names(deleted), "digest", digest);
        }
        private static Map<String, Integer> names(Map<SourceKind, Integer> values) {
            Map<String, Integer> result = new LinkedHashMap<>(); values.entrySet().stream()
                    .sorted(Map.Entry.comparingByKey()).forEach(entry -> result.put(entry.getKey().name(), entry.getValue())); return result;
        }
    }

    public Diff compare(Snapshot before, Snapshot after, boolean includeUnchanged) {
        Map<String, CanonicalRecord> left = index(before.allRecords()); Map<String, CanonicalRecord> right = index(after.allRecords());
        Set<String> keys = new HashSet<>(left.keySet()); keys.addAll(right.keySet());
        List<Change> changes = new ArrayList<>(); Map<SourceKind, Integer> added = counts(), updated = counts(), deleted = counts();
        for (String compound : keys.stream().sorted().toList()) {
            CanonicalRecord oldValue = left.get(compound); CanonicalRecord newValue = right.get(compound);
            SourceKind source = oldValue == null ? newValue.kind() : oldValue.kind();
            String oldDigest = oldValue == null ? "" : digest(oldValue); String newDigest = newValue == null ? "" : digest(newValue);
            ChangeType type;
            if (oldValue == null) { type = ChangeType.ADDED; added.merge(source, 1, Integer::sum); }
            else if (newValue == null) { type = ChangeType.DELETED; deleted.merge(source, 1, Integer::sum); }
            else if (!oldDigest.equals(newDigest)) { type = ChangeType.UPDATED; updated.merge(source, 1, Integer::sum); }
            else type = ChangeType.UNCHANGED;
            if (includeUnchanged || type != ChangeType.UNCHANGED) changes.add(new Change(source,
                    oldValue == null ? newValue.key() : oldValue.key(), type, oldDigest, newDigest,
                    oldValue == null ? -1 : oldValue.observedSequence(), newValue == null ? -1 : newValue.observedSequence()));
        }
        changes.sort(Comparator.comparing(Change::source).thenComparing(Change::key));
        String digest = Domain.sha256(io.jenkins.plugins.insights.json.Json.write(changes.stream().map(Change::toMap).toList()));
        return new Diff(List.copyOf(changes), Map.copyOf(added), Map.copyOf(updated), Map.copyOf(deleted), digest);
    }

    private Map<String, CanonicalRecord> index(Collection<CanonicalRecord> records) {
        Map<String, CanonicalRecord> result = new LinkedHashMap<>();
        for (CanonicalRecord record : records) result.put(record.kind().name() + ":" + record.key(), record); return result;
    }
    private String digest(CanonicalRecord record) { return Domain.sha256(io.jenkins.plugins.insights.json.Json.write(record.toMap())); }
    private Map<SourceKind, Integer> counts() { return new EnumMap<>(SourceKind.class); }
}
