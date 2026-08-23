package com.example.pii;

import com.example.pii.checkpoint.CheckpointStore;
import com.example.pii.detect.Detection;
import com.example.pii.policy.ScanPolicy;
import com.example.pii.privacy.Evidence;
import com.example.pii.protocol.Protocol;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class WorkerMain {
    public static void main(String[] arguments) throws Exception {
        String workerId = option(arguments, "--worker-id", "worker-local");
        String sessionId = option(arguments, "--session-id", "session-" + Instant.now().toEpochMilli());
        String checkpointPath = option(arguments, "--checkpoints", "/app/enterprise-pii/state/worker-checkpoints");
        byte[] key = key(option(arguments, "--fingerprint-key", "c3ludGhldGljLW9mZmxpbmUtd29ya2VyLWtleS0wMDAwMQ=="));
        ScannerEngine engine = new ScannerEngine(Detection.Registry.builtins(), new Evidence(key), defaultPolicy(), new CheckpointStore(Path.of(checkpointPath)));
        if (contains(arguments, "--scan-once")) {
            Protocol.Lease lease = new Protocol.Lease(
                option(arguments, "--tenant", "synthetic-enterprise"),
                option(arguments, "--job", "local-job"),
                option(arguments, "--shard", "local-shard"),
                Long.parseLong(option(arguments, "--generation", "1")),
                option(arguments, "--policy-digest", "starter-policy-digest"),
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
            Protocol.Batch batch = engine.batch(lease, outcome, 1, "", true);
            System.out.println(Protocol.canonicalJson(batch));
            return;
        }
        System.out.println(Protocol.canonicalJson(Map.of(
                "detector_bundle", "builtin-1",
                "formats", List.of("csv", "email", "json", "ndjson", "properties", "text", "xml", "zip"),
                "protocol_version", Protocol.VERSION,
                "session_id", sessionId,
                "type", "hello",
                "worker_id", workerId)));
        try (BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = input.readLine()) != null) {
                if (line.isBlank()) continue;
                if (line.contains("\"type\":\"shutdown\"")) break;
                if (line.contains("\"type\":\"heartbeat\"")) {
                    System.out.println(Protocol.canonicalJson(Map.of("protocol_version", Protocol.VERSION, "session_id", sessionId, "type", "heartbeat", "worker_id", workerId)));
                    continue;
                }
                System.out.println(Protocol.canonicalJson(Map.of("detail", "unsupported inbound frame", "protocol_version", Protocol.VERSION, "type", "error")));
            }
        }
    }

    private static ScanPolicy defaultPolicy() {
        return new ScanPolicy(
                "policy-2026-08",
                "starter-policy-digest",
                "epoch-07",
                "builtin-1",
                0.72,
                Set.of("EMAIL", "PHONE", "US_SSN", "PAYMENT_CARD", "IBAN", "PASSPORT", "TAX_ID", "DOB", "ADDRESS", "PERSON_NAME"),
                List.of(),
                List.of(),
                100,
                200);
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
}
