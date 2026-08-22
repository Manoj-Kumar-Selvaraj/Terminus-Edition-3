package io.jenkins.plugins.insights.query;

import io.jenkins.plugins.insights.analysis.AnalysisEngine;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.Page;
import io.jenkins.plugins.insights.model.Domain.Snapshot;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collection;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.Predicate;

/** Shared read-only query contract used by command-line and HTTP transports. */
public final class QueryService {
    public enum View { RECORDS, QUEUE, BUILDS, LINEAGE, PLUGINS, SUMMARY }
    public enum SortDirection { ASC, DESC }

    public record Principal(String name, boolean systemRead, boolean overallRead, Set<String> readableItemKeys) {
        public Principal {
            name = name == null ? "anonymous" : name;
            readableItemKeys = Set.copyOf(readableItemKeys == null ? Set.of() : readableItemKeys);
        }
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
            String owner = owner(record);
            return owner.isBlank() || principal.readableItemKeys().contains(owner) || principal.readableItemKeys().contains(record.key());
        }
        private String owner(CanonicalRecord record) {
            return switch (record.kind()) {
                case JOB -> record.key();
                case BUILD -> ((Domain.BuildRecord) record).jobKey();
                case QUEUE -> ((Domain.QueueRecord) record).taskKey();
                case FINGERPRINT -> ((Domain.FingerprintRecord) record).producerBuildKey();
                case NODE, PLUGIN -> "";
            };
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

    public record Response(String generationId, View view, List<Map<String, Object>> items,
                           int total, String nextCursor, Map<String, Long> facets,
                           Map<String, Object> metadata) {
        public Map<String, Object> toMap() {
            return Domain.ordered("generationId", generationId, "view", view.name().toLowerCase(Locale.ROOT),
                    "items", items, "total", total, "nextCursor", nextCursor.isBlank() ? null : nextCursor,
                    "facets", facets, "metadata", metadata);
        }
    }

    private final AccessPolicy access;
    private final VisibilityProjection visibility;
    public QueryService(AccessPolicy access) {
        this.access = Objects.requireNonNull(access); this.visibility = new VisibilityProjection(access);
    }

    public Response execute(String generationId, Snapshot snapshot, AnalysisEngine.Analysis analysis,
                            Principal principal, Request request) {
        if (!access.mayReadSystem(principal)) throw new SecurityException("Overall/Read and system insight permission required");
        List<CanonicalRecord> records = select(snapshot, request);
        Map<String, Long> facets = facets(records);
        records.sort(comparator(request));
        int start = decodeCursor(request.cursor(), records.size());
        int end = Math.min(records.size(), start + request.limit());
        List<CanonicalRecord> page = new ArrayList<>(records.subList(start, end));
        VisibilityProjection.Projection projected = visibility.project(principal, page);
        List<Map<String, Object>> items = projected.records().stream().map(CanonicalRecord::toMap).toList();
        String next = end < records.size() ? encodeCursor(end) : "";
        Map<String, Object> metadata = Domain.ordered("principal", principal.name(), "sort", request.sortField(),
                "direction", request.direction().name(), "visible", items.size(), "checkpoint", snapshot.checkpoint().toMap());
        if (request.view() != View.RECORDS) {
            Map<String, Object> selected = switch (request.view()) {
                case QUEUE -> analysis.queue().toMap();
                case BUILDS -> Domain.ordered("jobs", analysis.buildHealth().stream().map(AnalysisEngine.BuildHealth::toMap).toList());
                case LINEAGE -> analysis.lineage().toMap();
                case PLUGINS -> analysis.plugins().toMap();
                case SUMMARY -> summary(snapshot, analysis);
                case RECORDS -> Map.of();
            };
            items = List.of(selected);
        }
        return new Response(generationId, request.view(), items, records.size(), next, facets, metadata);
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
            case "display" -> Comparator.comparing(record -> String.valueOf(record.toMap().get("identity")));
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
        return Domain.ordered("records", snapshot.recordCount(), "errors", snapshot.errors().size(),
                "unsupportedSources", snapshot.unsupportedSources().stream().map(Enum::name).toList(),
                "queueDemand", analysis.queue().demand(), "queueCapacity", analysis.queue().capacity(),
                "lineageEdges", analysis.lineage().edges().size(), "plugins", analysis.plugins().plugins().size());
    }

    private String encodeCursor(int offset) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(("v1:" + offset).getBytes(StandardCharsets.UTF_8));
    }
    private int decodeCursor(String cursor, int size) {
        if (cursor == null || cursor.isBlank()) return 0;
        try {
            String decoded = new String(Base64.getUrlDecoder().decode(cursor), StandardCharsets.UTF_8);
            if (!decoded.startsWith("v1:")) throw new IllegalArgumentException("unsupported cursor version");
            int offset = Integer.parseInt(decoded.substring(3));
            if (offset < 0 || offset > size) throw new IllegalArgumentException("cursor is outside result set");
            return offset;
        } catch (IllegalArgumentException invalid) { throw new IllegalArgumentException("invalid cursor", invalid); }
    }
}
