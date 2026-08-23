package com.example.pii.privacy;

import com.example.pii.detect.Detection.Candidate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.HexFormat;

public final class Evidence {
    private final byte[] rootKey;

    public Evidence(byte[] rootKey) {
        if (rootKey.length < 32) throw new IllegalArgumentException("fingerprint root key must contain at least 256 bits");
        this.rootKey = rootKey.clone();
    }

    public Protected protect(Candidate candidate, String tenant, String scanScope, String keyEpoch) {
        String context = tenant + "\u001f" + scanScope + "\u001f" + keyEpoch + "\u001f" + candidate.category();
        byte[] derived = hmac(rootKey, context.getBytes(StandardCharsets.UTF_8));
        byte[] fingerprint = hmac(derived, candidate.normalizedValue().getBytes(StandardCharsets.UTF_8));
        return new Protected(mask(candidate.category(), candidate.normalizedValue()), HexFormat.of().formatHex(fingerprint));
    }

    public String stableFindingId(String fingerprint, String source, String member, String record, String field, long start, long end) {
        String identity = String.join("\u001f", fingerprint, source, member, record, field, Long.toString(start), Long.toString(end));
        return HexFormat.of().formatHex(hmac(rootKey, identity.getBytes(StandardCharsets.UTF_8))).substring(0, 32);
    }

    private String mask(String category, String value) {
        String punctuation = value.replaceAll("[\\p{L}\\p{N}]", "");
        int visible = switch (category) {
            case "PAYMENT_CARD", "IBAN" -> 4;
            case "EMAIL" -> 0;
            case "PHONE", "US_SSN" -> 2;
            default -> 1;
        };
        if (category.equals("EMAIL")) {
            int at = value.lastIndexOf('@');
            if (at <= 0) return "***";
            return "***@" + value.substring(at + 1);
        }
        String alphanumeric = value.replaceAll("[^\\p{L}\\p{N}]", "");
        if (alphanumeric.length() <= visible) return "*".repeat(Math.max(3, alphanumeric.length()));
        String suffix = alphanumeric.substring(alphanumeric.length() - visible);
        return "*".repeat(Math.max(3, alphanumeric.length() - visible)) + suffix + punctuation;
    }

    private byte[] hmac(byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(value);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException(exception);
        }
    }

    public record Protected(String maskedEvidence, String fingerprint) {}
}