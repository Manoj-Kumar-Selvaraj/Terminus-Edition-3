package io.jenkins.plugins.insights.query;

import io.jenkins.plugins.insights.analysis.AnalysisEngine;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.*;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.Predicate;

public final class QueryService {
    public enum View { RECORDS, QUEUE, BUILDS, LINEAGE, PLUGINS, SUMMARY }
    public enum SortDirection { ASC, DESC }

    public record Principal(String name, boolean systemRead, boolean overallRead, Set<String> readableItemKeys) {
        public Principal { name = name == null ? "anonymous" : name; readableItemKeys = Set.copyOf(readableItemKeys == null ? Set.of() : readableItemKeys); }
        public static Principal administrator() { return new Principal("operator", true, true, Set.of("*")); }
    }
    public interface AccessPolicy {
        boolean mayReadSystem(Principal principal);
        boolean mayReadRecord(Principal principal, CanonicalRecord record);
    }
    public static final class JenkinsStyleAccessPolicy implements AccessPolicy {
        public boolean mayReadSystem(Principal principal) { return principal.systemRead() && principal.overallRead(); }
        public boolean mayReadRecord(Principal principal, CanonicalRecord record) {
            if (!mayReadSystem(principal)) return false;
            if (principal.readableItemKeys().contains("*")) return true;
            String owner = switch (record.kind()) {
                case JOB -> record.key(); case BUILD -> ((BuildRecord) record).jobKey();
                case QUEUE -> ((QueueRecord) record).taskKey(); case FINGERPRINT, NODE, PLUGIN -> "";
            };
            return owner.isBlank() || principal.readableItemKeys().contains(owner);
        }
    }
    public record Request(View view, Set<SourceKind> kinds, String contains, String sortField,
                          SortDirection direction, int limit, String cursor) {
        public Request {
            Objects.requireNonNull(view, "view"); kinds = Set.copyOf(kinds == null ? Set.of() : kinds);
            contains = contains == null ? "" : contains; sortField = sortField == null ? "key" : sortField;
            Objects.requireNonNull(direction, "direction"); cursor = cursor == null ? "" : cursor;
            if (limit < 1 || limit > 1000) throw new IllegalArgumentException("limit must be between 1 and 1000");
        }
        public static Request records(int limit) { return new Request(View.RECORDS, Set.of(), "", "key", SortDirection.ASC, limit, ""); }
    }
    public record Response(String generationId, View view, List<Map<String, Object>> items, int total,
                           String nextCursor, Map<String, Long> facets, Map<String, Object> metadata) {
        public Map<String, Object> toMap() { return Domain.ordered("generationId", generationId,
                "view", view.name().toLowerCase(Locale.ROOT), "items", items, "total", total,
                "nextCursor", nextCursor.isBlank() ? null : nextCursor, "facets", facets, "metadata", metadata); }
    }

    private final AccessPolicy access;
    private final VisibilityProjection visibility;
    private final AnalysisEngine analyzer = new AnalysisEngine();
    public QueryService(AccessPolicy access) { this.access = Objects.requireNonNull(access); visibility = new VisibilityProjection(access); }

    public Response execute(String generationId, Snapshot snapshot, AnalysisEngine.Analysis ignored,
                            Principal principal, Request request) {
        if (!access.mayReadSystem(principal)) throw new SecurityException("Overall/Read and system insight permission required");
        VisibilityProjection.Projection initial = visibility.project(principal, snapshot.allRecords());
        boolean administrator = principal.readableItemKeys().contains("*");
        List<CanonicalRecord> authorized = initial.records().stream().filter(record -> administrator
            || !(record instanceof FingerprintRecord fingerprint)
            || visibility.lineageEndpointVisible(initial, fingerprint, snapshot.builds())).toList();
        Snapshot projected = snapshot(authorized, visibleErrors(snapshot, principal, initial), snapshot.checkpoint());
        AnalysisEngine.Analysis analysis = analyzer.analyze(projected, observationTime(projected));
        List<CanonicalRecord> records = select(projected, request); Map<String, Long> facets = facets(records);
        records.sort(comparator(request)); String binding = binding(generationId, request);
        int start = decodeCursor(request.cursor(), records.size(), binding); int end = Math.min(records.size(), start + request.limit());
        List<Map<String, Object>> items = records.subList(start, end).stream().map(CanonicalRecord::toMap).toList();
        String next = end < records.size() ? encodeCursor(end, binding) : "";
        if (request.view() != View.RECORDS) {
            Map<String, Object> selected = switch (request.view()) {
                case QUEUE -> analysis.queue().toMap();
                case BUILDS -> Domain.ordered("jobs", analysis.buildHealth().stream().map(AnalysisEngine.BuildHealth::toMap).toList());
                case LINEAGE -> analysis.lineage().toMap(); case PLUGINS -> analysis.plugins().toMap();
                case SUMMARY -> summary(projected, analysis); case RECORDS -> Map.of();
            };
            items = List.of(selected); next = "";
        }
        Map<String, Object> metadata = Domain.ordered("principal", principal.name(), "sort", request.sortField(),
                "direction", request.direction().name(), "visible", records.size(), "checkpoint", projected.checkpoint().toMap());
        return new Response(generationId, request.view(), items, records.size(), next, facets, metadata);
    }

    private Snapshot snapshot(Collection<CanonicalRecord> records, List<SourceError> errors, Checkpoint checkpoint) {
        Map<String, JobRecord> jobs = new LinkedHashMap<>(); Map<String, BuildRecord> builds = new LinkedHashMap<>();
        Map<String, QueueRecord> queue = new LinkedHashMap<>(); Map<String, NodeRecord> nodes = new LinkedHashMap<>();
        Map<String, FingerprintRecord> fingerprints = new LinkedHashMap<>(); Map<String, PluginRecord> plugins = new LinkedHashMap<>();
        for (CanonicalRecord record : records) {
            if (record instanceof JobRecord value) jobs.put(value.key(), value); else if (record instanceof BuildRecord value) builds.put(value.key(), value);
            else if (record instanceof QueueRecord value) queue.put(value.key(), value); else if (record instanceof NodeRecord value) nodes.put(value.key(), value);
            else if (record instanceof FingerprintRecord value) fingerprints.put(value.key(), value); else if (record instanceof PluginRecord value) plugins.put(value.key(), value);
        }
        return new Snapshot(jobs, builds, queue, nodes, fingerprints, plugins, errors, Set.of(), checkpoint);
    }

    private List<SourceError> visibleErrors(Snapshot snapshot, Principal principal, VisibilityProjection.Projection projection) {
        boolean administrator = principal.readableItemKeys().contains("*");
        Set<String> visible = projection.records().stream().map(CanonicalRecord::key).collect(java.util.stream.Collectors.toSet());
        Set<String> visibleOwners = projection.visibleJobs();
        return snapshot.errors().stream().filter(error -> !error.code().equals("DELETE_FENCE"))
            .filter(error -> administrator || (!error.recordKey().isBlank()
                && (visible.contains(error.recordKey()) || visibleOwners.contains(error.recordKey())))).toList();
    }

    private long observationTime(Snapshot snapshot) {
        return Math.max(1_735_689_600_000L, snapshot.queue().values().stream().mapToLong(QueueRecord::enqueuedMillis).max().orElse(0));
    }
    private List<CanonicalRecord> select(Snapshot snapshot, Request request) {
        Predicate<CanonicalRecord> kind = request.kinds().isEmpty() ? ignored -> true : record -> request.kinds().contains(record.kind());
        String needle = request.contains().toLowerCase(Locale.ROOT);
        Predicate<CanonicalRecord> contains = needle.isBlank() ? ignored -> true
                : record -> Json.write(record.toMap()).toLowerCase(Locale.ROOT).contains(needle);
        return snapshot.allRecords().stream().filter(kind.and(contains)).collect(java.util.stream.Collectors.toCollection(ArrayList::new));
    }
    private Comparator<CanonicalRecord> comparator(Request request) {
        Comparator<CanonicalRecord> comparator = switch (request.sortField()) {
            case "kind" -> Comparator.comparing(record -> record.kind().name());
            case "sequence" -> Comparator.comparingLong(CanonicalRecord::observedSequence);
            case "display" -> Comparator.comparing(record -> ((Map<?, ?>) record.toMap().get("identity")).get("display").toString());
            case "key" -> Comparator.comparing(CanonicalRecord::key);
            default -> throw new IllegalArgumentException("unsupported sort field: " + request.sortField());
        };
        comparator = comparator.thenComparing(record -> record.kind().name()).thenComparing(CanonicalRecord::key);
        return request.direction() == SortDirection.DESC ? comparator.reversed() : comparator;
    }
    private Map<String, Long> facets(Collection<CanonicalRecord> records) {
        Map<String, Long> result = new TreeMap<>();
        for (CanonicalRecord record : records) result.merge(record.kind().name().toLowerCase(Locale.ROOT), 1L, Long::sum);
        return Map.copyOf(result);
    }
    private Map<String, Object> summary(Snapshot snapshot, AnalysisEngine.Analysis analysis) {
        return Domain.ordered("records", snapshot.recordCount(), "errors", snapshot.errors().size(), "unsupportedSources", List.of(),
                "queueDemand", analysis.queue().demand(), "queueCapacity", analysis.queue().capacity(),
                "lineageEdges", analysis.lineage().edges().size(), "plugins", analysis.plugins().plugins().size());
    }
    private String binding(String generationId, Request request) {
        return Domain.sha256(Json.write(Domain.ordered("generation", generationId, "view", request.view().name(),
                "kinds", request.kinds().stream().map(Enum::name).sorted().toList(), "contains", request.contains(),
                "sort", request.sortField(), "direction", request.direction().name()))).substring(0, 16);
    }
    private String encodeCursor(int offset, String binding) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(("v1:" + binding + ":" + offset).getBytes(StandardCharsets.UTF_8));
    }
    private int decodeCursor(String cursor, int size, String binding) {
        if (cursor == null || cursor.isBlank()) return 0;
        try {
            String decoded = new String(Base64.getUrlDecoder().decode(cursor), StandardCharsets.UTF_8);
            String[] parts = decoded.split(":", -1);
            if (parts.length != 3 || !parts[0].equals("v1") || !parts[1].equals(binding)) throw new IllegalArgumentException("cursor does not match query");
            int offset = Integer.parseInt(parts[2]); if (offset < 0 || offset > size) throw new IllegalArgumentException("cursor is outside result set");
            return offset;
        } catch (IllegalArgumentException invalid) { throw new IllegalArgumentException("invalid cursor", invalid); }
    }
}