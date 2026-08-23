package com.example.pii.protocol;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.math.BigDecimal;

public final class Protocol {
    public static final String VERSION = "1";

    private static final Set<String> LOCATION_OMIT_EMPTY = Set.of("archive_member");
    private static final Set<String> SCAN_ERROR_OMIT_EMPTY = Set.of("record_id", "field_path");
    private static final Set<String> TRUNCATION_OMIT_EMPTY = Set.of("checkpoint");

    public record Lease(
            String tenant,
            String jobId,
            String shardId,
            long generation,
            String policyDigest,
            String corpusDigest,
            String workerId,
            String sessionId,
            int attempt,
            String token,
            Instant issuedAt,
            Instant deadline,
            String sourceRoot,
            String sourceId) {
        public Lease {
            Objects.requireNonNull(tenant);
            Objects.requireNonNull(jobId);
            Objects.requireNonNull(shardId);
            Objects.requireNonNull(policyDigest);
            Objects.requireNonNull(sessionId);
            Objects.requireNonNull(token);
            Objects.requireNonNull(deadline);
        }
    }

    public record Location(
            String sourceId,
            String canonicalPath,
            String archiveMember,
            String recordId,
            String fieldPath,
            long line,
            long byteStart,
            long byteEnd) implements Comparable<Location> {
        @Override
        public int compareTo(Location other) {
            int value = sourceId.compareTo(other.sourceId);
            if (value == 0) value = canonicalPath.compareTo(other.canonicalPath);
            if (value == 0) value = archiveMember.compareTo(other.archiveMember);
            if (value == 0) value = recordId.compareTo(other.recordId);
            if (value == 0) value = fieldPath.compareTo(other.fieldPath);
            if (value == 0) value = Long.compare(byteStart, other.byteStart);
            return value == 0 ? Long.compare(byteEnd, other.byteEnd) : value;
        }
    }

    public record Finding(
            String id,
            String category,
            String maskedEvidence,
            String fingerprint,
            double confidence,
            String detectorRevision,
            String policyVersion,
            String policyDigest,
            Location location,
            List<String> lineage,
            boolean suppressed) {
        public Finding {
            lineage = List.copyOf(lineage);
        }
    }

    public record ScanError(
            String kind,
            String sourceId,
            String recordId,
            String fieldPath,
            String detail,
            boolean recoverable) {}

    public record Truncation(
            String budget,
            String sourceId,
            long limit,
            long observed,
            String checkpoint) {}

    public record Batch(
            String id,
            String bodyDigest,
            String jobId,
            String shardId,
            long generation,
            String policyDigest,
            String sessionId,
            int attempt,
            String leaseToken,
            long sequence,
            String previousCheckpoint,
            String nextCheckpoint,
            List<Finding> findings,
            List<ScanError> errors,
            List<Truncation> truncations,
            boolean complete) {}

    public static String canonicalJson(Object value) {
        StringBuilder output = new StringBuilder();
        appendJson(output, value);
        return output.toString();
    }

    public static String canonicalBatchDigest(Batch batch) {
        Map<String, Object> digestBody = new TreeMap<>();
        digestBody.put("errors", batch.errors());
        digestBody.put("findings", sortedFindingsForDigest(batch.findings()));
        digestBody.put("next_checkpoint", batch.nextCheckpoint());
        digestBody.put("sequence", batch.sequence());
        digestBody.put("truncations", batch.truncations());
        return sha256(canonicalJson(digestBody));
    }

    private static void appendJson(StringBuilder output, Object value) {
        if (value == null) {
            output.append("null");
        } else if (value instanceof String text) {
            quote(output, text);
        } else if (value instanceof Boolean) {
            output.append(value);
        } else if (value instanceof Number number) {
            output.append(formatNumber(number));
        } else if (value instanceof Instant instant) {
            quote(output, instant.toString());
        } else if (value instanceof Map<?, ?> map) {
            output.append('{');
            boolean comma = false;
            if (map instanceof LinkedHashMap<?, ?>) {
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    if (comma) output.append(',');
                    quote(output, String.valueOf(entry.getKey()));
                    output.append(':');
                    appendJson(output, entry.getValue());
                    comma = true;
                }
            } else {
                TreeMap<String, Object> sorted = new TreeMap<>();
                map.forEach((key, item) -> sorted.put(String.valueOf(key), item));
                for (Map.Entry<String, Object> entry : sorted.entrySet()) {
                    if (comma) output.append(',');
                    quote(output, entry.getKey());
                    output.append(':');
                    appendJson(output, entry.getValue());
                    comma = true;
                }
            }
            output.append('}');
        } else if (value instanceof Collection<?> collection) {
            output.append('[');
            boolean comma = false;
            for (Object item : collection) {
                if (comma) output.append(',');
                appendJson(output, item);
                comma = true;
            }
            output.append(']');
        } else if (value.getClass().isRecord()) {
            appendRecord(output, value);
        } else {
            quote(output, String.valueOf(value));
        }
    }

    private static void appendRecord(StringBuilder output, Object value) {
        Map<String, Object> fields = new LinkedHashMap<>();
        Set<String> omitEmpty = omitEmptyFields(value.getClass().getSimpleName());
        for (var component : value.getClass().getRecordComponents()) {
            try {
                Object fieldValue = component.getAccessor().invoke(value);
                String key = toSnakeCase(component.getName());
                if (omitEmpty.contains(key) && fieldValue instanceof String text && text.isEmpty()) {
                    continue;
                }
                fields.put(key, fieldValue);
            } catch (ReflectiveOperationException exception) {
                throw new IllegalArgumentException("cannot encode record", exception);
            }
        }
        appendJson(output, fields);
    }

    private static Set<String> omitEmptyFields(String simpleName) {
        return switch (simpleName) {
            case "Location" -> LOCATION_OMIT_EMPTY;
            case "ScanError" -> SCAN_ERROR_OMIT_EMPTY;
            case "Truncation" -> TRUNCATION_OMIT_EMPTY;
            default -> Set.of();
        };
    }

    private static String formatNumber(Number number) {
        if (number instanceof Double value) {
            if (value.isNaN() || value.isInfinite()) return "null";
            if (value == Math.rint(value)) return Long.toString(value.longValue());
            return BigDecimal.valueOf(value).stripTrailingZeros().toPlainString();
        }
        if (number instanceof Float value) {
            if (value.isNaN() || value.isInfinite()) return "null";
            if (value == Math.rint(value)) return Long.toString(value.longValue());
            return BigDecimal.valueOf(value).stripTrailingZeros().toPlainString();
        }
        return number.toString();
    }

    private static String toSnakeCase(String name) {
        StringBuilder output = new StringBuilder(name.length() + 4);
        for (int index = 0; index < name.length(); index++) {
            char character = name.charAt(index);
            if (Character.isUpperCase(character)) {
                if (index > 0) output.append('_');
                output.append(Character.toLowerCase(character));
            } else {
                output.append(character);
            }
        }
        return output.toString();
    }

    private static void quote(StringBuilder output, String value) {
        output.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (character < 0x20) output.append(String.format("\\u%04x", (int) character));
                    else output.append(character);
                }
            }
        }
        output.append('"');
    }

    public static String sha256(String text) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }

    public static List<Finding> sortedFindings(Collection<Finding> findings) {
        ArrayList<Finding> copy = new ArrayList<>(findings);
        copy.sort(Comparator.comparing(Finding::location)
                .thenComparing(Finding::category)
                .thenComparing(Finding::fingerprint)
                .thenComparing(Finding::detectorRevision));
        return List.copyOf(copy);
    }

    public static List<Finding> sortedFindingsForDigest(Collection<Finding> findings) {
        ArrayList<Finding> copy = new ArrayList<>(findings);
        copy.sort(Comparator.comparing((Finding finding) -> finding.location().sourceId())
                .thenComparing(finding -> finding.location().canonicalPath())
                .thenComparing(finding -> finding.location().archiveMember())
                .thenComparing(finding -> finding.location().recordId())
                .thenComparing(finding -> finding.location().fieldPath())
                .thenComparingLong(finding -> finding.location().byteStart())
                .thenComparing(Finding::category)
                .thenComparing(Finding::fingerprint)
                .thenComparing(Finding::detectorRevision));
        return List.copyOf(copy);
    }

    private Protocol() {}
}
