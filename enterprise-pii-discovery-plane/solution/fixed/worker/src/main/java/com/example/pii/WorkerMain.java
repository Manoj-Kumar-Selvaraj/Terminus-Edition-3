package com.example.pii;

import com.example.pii.checkpoint.CheckpointStore;
import com.example.pii.detect.Detection;
import com.example.pii.policy.ScanPolicy;
import com.example.pii.privacy.Evidence;
import com.example.pii.protocol.Protocol;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class WorkerMain {
    private static final Pattern CONFIG_FIELD = Pattern.compile("\"(policy_file)\"\\s*:\\s*\"([^\"]+)\"");

    public static void main(String[] arguments) throws Exception {
        String workerId = option(arguments, "--worker-id", "worker-local");
        String sessionId = option(arguments, "--session-id", "session-" + Instant.now().toEpochMilli());
        String checkpointPath = option(arguments, "--checkpoints", "/app/enterprise-pii/state/worker-checkpoints");
        byte[] key = key(option(arguments, "--fingerprint-key", "c3ludGhldGljLW9mZmxpbmUtd29ya2VyLWtleS0wMDAwMQ=="));
        ScanPolicy policy = loadPolicy(arguments);
        ScannerEngine engine = new ScannerEngine(Detection.Registry.builtins(), new Evidence(key), policy, new CheckpointStore(Path.of(checkpointPath)));
        if (contains(arguments, "--scan-once")) {
            Protocol.Lease lease = new Protocol.Lease(
                option(arguments, "--tenant", "synthetic-enterprise"),
                option(arguments, "--job", "local-job"),
                option(arguments, "--shard", "local-shard"),
                Long.parseLong(option(arguments, "--generation", "1")),
                option(arguments, "--policy-digest", policy.digest()),
                option(arguments, "--corpus-digest", "local-corpus"),
                workerId,
                sessionId,
                Integer.parseInt(option(arguments, "--attempt", "1")),
                option(arguments, "--lease-token", "local-lease"),
                Instant.now(),
                Instant.now().plusSeconds(3600),
                option(arguments, "--source-root", "/app/enterprise-pii/corpus"),
                option(arguments, "--source-id", "local-source"));
            ScannerEngine.SourceContext context = new ScannerEngine.SourceContext(
                option(arguments, "--department", "engineering"),
                option(arguments, "--region", "na"));
            ScannerEngine.Outcome outcome = engine.scan(lease, context);
            long sequence = engine.nextSequence(lease);
            String previousCheckpoint = engine.previousCheckpoint(lease);
            Protocol.Batch batch = engine.batch(lease, outcome, sequence, previousCheckpoint, true);
            System.out.println(Protocol.canonicalJson(batch));
            return;
        }
        emitEnvelope("hello", newRequestId(), Map.of(
                "detector_bundle", policy.detectorBundle(),
                "formats", List.of("csv", "email", "json", "ndjson", "properties", "text", "xml", "zip"),
                "session_id", sessionId,
                "worker_id", workerId));
        try (BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = input.readLine()) != null) {
                if (line.isBlank()) continue;
                Map<String, Object> envelope = Json.parseObject(line);
                String type = string(envelope.get("type"));
                String requestId = string(envelope.get("request_id"));
                String protocolVersion = string(envelope.get("protocol_version"));
                if (!Protocol.VERSION.equals(protocolVersion)) {
                    emitError(requestId, "unsupported protocol version");
                    continue;
                }
                switch (type) {
                    case "shutdown", "cancel" -> { return; }
                    case "heartbeat" -> emitEnvelope("heartbeat", requestId, Map.of(
                            "session_id", sessionId,
                            "worker_id", workerId));
                    case "lease" -> handleLease(engine, envelope, requestId, sessionId);
                    case "ack" -> { /* accepted batch acknowledgement */ }
                    default -> emitError(requestId, "unsupported inbound frame");
                }
            }
        }
    }

    private static void handleLease(ScannerEngine engine, Map<String, Object> envelope, String requestId, String sessionId) throws IOException {
        Map<String, Object> body = map(envelope.get("body"));
        Map<String, Object> leaseBody = map(body.get("lease"));
        Protocol.Lease lease = new Protocol.Lease(
                string(leaseBody.get("tenant")),
                string(leaseBody.get("job_id")),
                string(leaseBody.get("shard_id")),
                longValue(leaseBody.get("generation")),
                string(leaseBody.get("policy_digest")),
                stringOr(leaseBody.get("corpus_digest"), string(body.get("corpus_digest"))),
                stringOr(leaseBody.get("worker_id"), string(body.get("worker_id"))),
                stringOr(leaseBody.get("session_id"), sessionId),
                (int) longValue(leaseBody.get("attempt")),
                string(leaseBody.get("token")),
                Instant.parse(string(leaseBody.get("issued_at"))),
                Instant.parse(string(leaseBody.get("deadline"))),
                string(body.get("source_root")),
                string(body.get("source_id")));
        ScannerEngine.SourceContext context = new ScannerEngine.SourceContext(
                string(body.get("department")),
                string(body.get("region")));
        ScannerEngine.Outcome outcome = engine.scan(lease, context);
        long sequence = engine.nextSequence(lease);
        String previousCheckpoint = engine.previousCheckpoint(lease);
        Protocol.Batch batch = engine.batch(lease, outcome, sequence, previousCheckpoint, true);
        emitEnvelope("batch", requestId, batchBody(batch));
    }

    private static Map<String, Object> batchBody(Protocol.Batch batch) {
        LinkedHashMap<String, Object> body = new LinkedHashMap<>();
        body.put("attempt", batch.attempt());
        body.put("body_digest", batch.bodyDigest());
        body.put("complete", batch.complete());
        body.put("errors", batch.errors());
        body.put("findings", batch.findings());
        body.put("generation", batch.generation());
        body.put("id", batch.id());
        body.put("job_id", batch.jobId());
        body.put("lease_token", batch.leaseToken());
        body.put("next_checkpoint", batch.nextCheckpoint());
        body.put("policy_digest", batch.policyDigest());
        body.put("previous_checkpoint", batch.previousCheckpoint());
        body.put("sequence", batch.sequence());
        body.put("session_id", batch.sessionId());
        body.put("shard_id", batch.shardId());
        body.put("truncations", batch.truncations());
        return body;
    }

    private static ScanPolicy loadPolicy(String[] arguments) throws IOException {
        String digestOverride = env("PII_POLICY_DIGEST", "");
        if (!digestOverride.isBlank()) {
            return policyFromDigest(digestOverride);
        }
        String configPath = option(arguments, "--config", env("PII_CONFIG", "/app/enterprise-pii/config/system.json"));
        String policyPath = option(arguments, "--policy-file", policyFileFromConfig(configPath));
        String raw = Files.readString(Path.of(policyPath), StandardCharsets.UTF_8);
        Map<String, Object> document = Json.parseObject(raw);
        String digest = canonicalPolicyDigest(document);
        Map<String, Object> budgets = map(document.get("budgets"));
        return new ScanPolicy(
                string(document.get("version")),
                digest,
                string(document.get("key_epoch")),
                string(document.get("detector_bundle")),
                doubleValue(document.get("minimum_confidence")),
                new TreeSet<>(strings(document.get("categories"))),
                parseRules(list(document.get("allowlist"))),
                parseRules(list(document.get("suppressions"))),
                (int) longValue(budgets.get("max_matches_per_record")),
                (int) longValue(budgets.get("max_errors_per_source")));
    }

    private static ScanPolicy policyFromDigest(String digest) {
        return new ScanPolicy(
                "policy-2026-08",
                digest,
                "epoch-07",
                "builtin-1",
                0.72,
                Set.of("EMAIL", "PHONE", "US_SSN", "PAYMENT_CARD", "IBAN", "PASSPORT", "TAX_ID", "DOB", "ADDRESS", "PERSON_NAME"),
                List.of(),
                List.of(),
                100,
                200);
    }

    private static String policyFileFromConfig(String configPath) throws IOException {
        String raw = Files.readString(Path.of(configPath), StandardCharsets.UTF_8);
        Matcher matcher = CONFIG_FIELD.matcher(raw);
        if (matcher.find()) return matcher.group(2);
        return "/app/enterprise-pii/config/policy.json";
    }

    private static String canonicalPolicyDigest(Map<String, Object> document) {
        ArrayList<String> categories = new ArrayList<>(strings(document.get("categories")));
        categories.sort(String::compareTo);
        Map<String, Object> budgets = map(document.get("budgets"));
        StringBuilder output = new StringBuilder();
        output.append("{\"version\":").append(Json.quote(string(document.get("version"))));
        output.append(",\"digest\":\"\"");
        output.append(",\"key_epoch\":").append(Json.quote(string(document.get("key_epoch"))));
        output.append(",\"detector_bundle\":").append(Json.quote(string(document.get("detector_bundle"))));
        output.append(",\"minimum_confidence\":").append(doubleValue(document.get("minimum_confidence")));
        output.append(",\"categories\":").append(Json.encodeArray(categories));
        output.append(",\"budgets\":{");
        output.append("\"max_file_bytes\":").append(longValue(budgets.get("max_file_bytes")));
        output.append(",\"max_records_per_file\":").append(longValue(budgets.get("max_records_per_file")));
        output.append(",\"max_nesting\":").append(longValue(budgets.get("max_nesting")));
        output.append(",\"max_archive_entries\":").append(longValue(budgets.get("max_archive_entries")));
        output.append(",\"max_archive_bytes\":").append(longValue(budgets.get("max_archive_bytes")));
        output.append(",\"max_matches_per_record\":").append(longValue(budgets.get("max_matches_per_record")));
        output.append(",\"max_errors_per_source\":").append(longValue(budgets.get("max_errors_per_source")));
        output.append(",\"max_scan_seconds\":").append(longValue(budgets.get("max_scan_seconds")));
        output.append("},\"allowlist\":").append(Json.encodeArray(list(document.get("allowlist"))));
        output.append(",\"suppressions\":").append(Json.encodeArray(list(document.get("suppressions"))));
        output.append(",\"published_at\":\"0001-01-01T00:00:00Z\"}");
        return Protocol.sha256(output.toString());
    }

    private static List<ScanPolicy.Rule> parseRules(List<Object> rules) {
        ArrayList<ScanPolicy.Rule> output = new ArrayList<>();
        for (Object item : rules) {
            Map<String, Object> value = map(item);
            Instant expiresAt = null;
            Object expires = value.get("expires_at");
            if (expires != null && !"null".equals(String.valueOf(expires))) expiresAt = Instant.parse(string(expires));
            output.add(new ScanPolicy.Rule(
                    string(value.get("id")),
                    string(value.get("tenant")),
                    string(value.get("category")),
                    stringOr(value.get("department"), ""),
                    stringOr(value.get("region"), ""),
                    stringOr(value.get("source_id"), ""),
                    stringOr(value.get("fingerprint"), ""),
                    stringOr(value.get("policy_version"), ""),
                    expiresAt,
                    stringOr(value.get("reason"), "")));
        }
        return List.copyOf(output);
    }

    private static void emitEnvelope(String type, String requestId, Map<String, Object> body) {
        LinkedHashMap<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("body", body);
        envelope.put("protocol_version", Protocol.VERSION);
        envelope.put("request_id", requestId);
        envelope.put("type", type);
        System.out.println(Protocol.canonicalJson(envelope));
        System.out.flush();
    }

    private static void emitError(String requestId, String detail) {
        emitEnvelope("error", requestId, Map.of("detail", detail));
    }

    private static String newRequestId() {
        return UUID.randomUUID().toString();
    }

    private static byte[] key(String encoded) {
        byte[] value = Base64.getDecoder().decode(encoded);
        if (value.length < 32) throw new IllegalArgumentException("fingerprint key is too short");
        return value;
    }

    private static String option(String[] arguments, String name, String fallback) {
        for (int index = 0; index + 1 < arguments.length; index++) if (arguments[index].equals(name)) return arguments[index + 1];
        return fallback;
    }

    private static boolean contains(String[] arguments, String value) {
        for (String argument : arguments) if (argument.equals(value)) return true;
        return false;
    }

    private static String env(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        if (value instanceof Map<?, ?> map) return (Map<String, Object>) map;
        return Map.of();
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Object value) {
        if (value instanceof List<?> items) return (List<Object>) items;
        return List.of();
    }

    private static List<String> strings(Object value) {
        ArrayList<String> output = new ArrayList<>();
        for (Object item : list(value)) output.add(string(item));
        return output;
    }

    private static String string(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private static String stringOr(Object value, String fallback) {
        String text = string(value);
        return text.isBlank() ? fallback : text;
    }

    private static long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        return Long.parseLong(string(value));
    }

    private static double doubleValue(Object value) {
        if (value instanceof Number number) return number.doubleValue();
        return Double.parseDouble(string(value));
    }

    private static final class Json {
        private final String input;
        private int offset;

        private Json(String input) {
            this.input = input;
        }

        static Map<String, Object> parseObject(String input) {
            Object value = new Json(input).value();
            if (!(value instanceof Map<?, ?> map)) throw new IllegalArgumentException("json object expected");
            @SuppressWarnings("unchecked")
            Map<String, Object> object = (Map<String, Object>) map;
            return object;
        }

        static String quote(String value) {
            StringBuilder output = new StringBuilder();
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
            return output.toString();
        }

        static String encodeArray(List<?> values) {
            StringBuilder output = new StringBuilder("[");
            boolean comma = false;
            for (Object value : values) {
                if (comma) output.append(',');
                appendValue(output, value);
                comma = true;
            }
            output.append(']');
            return output.toString();
        }

        private static void appendValue(StringBuilder output, Object value) {
            if (value == null) output.append("null");
            else if (value instanceof String text) output.append(quote(text));
            else if (value instanceof Boolean || value instanceof Number) output.append(value);
            else if (value instanceof Map<?, ?> map) output.append(encodeObject(map));
            else if (value instanceof List<?> list) output.append(encodeArray(list));
            else output.append(quote(String.valueOf(value)));
        }

        private static String encodeObject(Map<?, ?> map) {
            StringBuilder output = new StringBuilder("{");
            boolean comma = false;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (comma) output.append(',');
                output.append(quote(String.valueOf(entry.getKey()))).append(':');
                appendValue(output, entry.getValue());
                comma = true;
            }
            output.append('}');
            return output.toString();
        }

        private Object value() {
            whitespace();
            return switch (peek()) {
                case '{' -> object();
                case '[' -> array();
                case '"' -> string();
                case 't' -> literal("true", Boolean.TRUE);
                case 'f' -> literal("false", Boolean.FALSE);
                case 'n' -> literal("null", null);
                default -> number();
            };
        }

        private Map<String, Object> object() {
            LinkedHashMap<String, Object> output = new LinkedHashMap<>();
            offset++;
            whitespace();
            if (take('}')) return output;
            while (true) {
                whitespace();
                String key = string();
                whitespace();
                require(':');
                output.put(key, value());
                whitespace();
                if (take('}')) return output;
                require(',');
            }
        }

        private List<Object> array() {
            ArrayList<Object> output = new ArrayList<>();
            offset++;
            whitespace();
            if (take(']')) return output;
            while (true) {
                output.add(value());
                whitespace();
                if (take(']')) return output;
                require(',');
            }
        }

        private String string() {
            require('"');
            StringBuilder output = new StringBuilder();
            while (offset < input.length()) {
                char character = input.charAt(offset++);
                if (character == '"') return output.toString();
                if (character != '\\') {
                    output.append(character);
                    continue;
                }
                char escaped = input.charAt(offset++);
                switch (escaped) {
                    case '"', '\\', '/' -> output.append(escaped);
                    case 'b' -> output.append('\b');
                    case 'f' -> output.append('\f');
                    case 'n' -> output.append('\n');
                    case 'r' -> output.append('\r');
                    case 't' -> output.append('\t');
                    case 'u' -> output.append((char) Integer.parseInt(input.substring(offset, offset + 4), 16));
                    default -> throw error("invalid escape");
                }
                if (escaped == 'u') offset += 4;
            }
            throw error("unterminated string");
        }

        private Number number() {
            int start = offset;
            if (take('-')) {}
            digits();
            boolean decimal = false;
            if (take('.')) { decimal = true; digits(); }
            if (take('e') || take('E')) {
                decimal = true;
                if (take('+') || take('-')) {}
                digits();
            }
            String token = input.substring(start, offset);
            return decimal ? Double.parseDouble(token) : Long.parseLong(token);
        }

        private Object literal(String token, Object value) {
            if (!input.startsWith(token, offset)) throw error("invalid literal");
            offset += token.length();
            return value;
        }

        private void digits() {
            int start = offset;
            while (offset < input.length() && Character.isDigit(input.charAt(offset))) offset++;
            if (start == offset) throw error("digit expected");
        }

        private void whitespace() {
            while (offset < input.length() && Character.isWhitespace(input.charAt(offset))) offset++;
        }

        private char peek() { return offset < input.length() ? input.charAt(offset) : '\0'; }
        private boolean take(char wanted) { if (peek() != wanted) return false; offset++; return true; }
        private void require(char wanted) { if (!take(wanted)) throw error("expected " + wanted); }
        private IllegalArgumentException error(String message) { return new IllegalArgumentException(message + " at " + offset); }
    }
}
