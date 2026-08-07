package com.freight.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Streaming SHA-256 helper shared by the journal and the selftest report. */
public final class Sha256Util {

    private final MessageDigest digest;

    public Sha256Util() {
        try {
            this.digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    public Sha256Util update(String text) {
        digest.update(text.getBytes(StandardCharsets.UTF_8));
        return this;
    }

    public String hex() {
        byte[] raw = digest.digest();
        StringBuilder out = new StringBuilder(raw.length * 2);
        for (int i = 0; i < raw.length; i++) {
            out.append(String.format(java.util.Locale.ROOT, "%02x", raw[i] & 0xFF));
        }
        return out.toString();
    }

    public static String of(String text) {
        return new Sha256Util().update(text).hex();
    }
}
