package com.example.pii.policy;

import com.example.pii.detect.Detection.Candidate;
import com.example.pii.read.RecordReader.Field;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Set;

public record ScanPolicy(
        String version,
        String digest,
        String keyEpoch,
        String detectorBundle,
        double minimumConfidence,
        Set<String> categories,
        List<Rule> allowlist,
        List<Rule> suppressions,
        int maximumMatchesPerRecord,
        int maximumErrorsPerSource) {

    public ScanPolicy {
        Objects.requireNonNull(version);
        Objects.requireNonNull(digest);
        Objects.requireNonNull(keyEpoch);
        Objects.requireNonNull(detectorBundle);
        categories = Set.copyOf(categories);
        allowlist = List.copyOf(allowlist);
        suppressions = List.copyOf(suppressions);
    }

    public record Rule(
            String id,
            String tenant,
            String category,
            String department,
            String region,
            String sourceId,
            String fingerprint,
            String policyVersion,
            Instant expiresAt,
            String reason) {
        public boolean activeAt(Instant now) { return expiresAt == null || expiresAt.isAfter(now); }
        public int specificity() {
            int value = 0;
            if (!empty(sourceId)) value += 8;
            if (!empty(department)) value += 4;
            if (!empty(region)) value += 2;
            if (!empty(fingerprint)) value += 1;
            return value;
        }
    }

    public Decision decide(Candidate candidate, Field field, String tenant, String department, String region, String fingerprint, Instant now) {
        ArrayList<Rule> matches = new ArrayList<>();
        for (Rule rule : allowlist) if (matches(rule, candidate, field, tenant, department, region, fingerprint, now)) matches.add(rule);
        for (Rule rule : suppressions) if (matches(rule, candidate, field, tenant, department, region, fingerprint, now)) matches.add(rule);
        matches.sort((left, right) -> Integer.compare(right.specificity(), left.specificity()));
        if (matches.isEmpty()) return new Decision(false, "", "");
        Rule winner = matches.getFirst();
        return new Decision(true, winner.id(), winner.reason());
    }

    private boolean matches(Rule rule, Candidate candidate, Field field, String tenant, String department, String region, String fingerprint, Instant now) {
        if (!rule.activeAt(now)) return false;
        if (!equal(rule.tenant(), tenant)) return false;
        if (!equal(rule.policyVersion(), version)) return false;
        if (!equal(rule.category(), candidate.category())) return false;
        if (!empty(rule.department()) && !rule.department().equals(department)) return false;
        if (!empty(rule.region()) && !rule.region().equals(region)) return false;
        if (!empty(rule.sourceId()) && !rule.sourceId().equals(field.provenance().sourceId())) return false;
        return empty(rule.fingerprint()) || rule.fingerprint().equals(fingerprint);
    }

    private static boolean equal(String expected, String actual) { return empty(expected) || expected.equals(actual); }
    private static boolean empty(String value) { return value == null || value.isBlank(); }

    public record Decision(boolean suppressed, String ruleId, String reason) {}
}
