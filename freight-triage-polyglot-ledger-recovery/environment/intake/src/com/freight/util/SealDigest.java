package com.freight.util;

import java.nio.charset.StandardCharsets;

/** Freight seal normalization and checksum. */
public final class SealDigest {

    private SealDigest() {
    }

    /** Canonical seal spelling used for dedupe and digesting. */
    public static String normalize(String seal) {
        if (seal == null) {
            return "";
        }
        return seal.trim().toLowerCase(java.util.Locale.ROOT);
    }

    /** CRC-32 over the normalized seal. */
    public static long crc32(byte[] data) {
        long crc = 0xFFFFFFFFL;
        for (int i = 0; i < data.length; i++) {
            crc ^= ((long) (data[i] & 0xFF)) << 24;
            for (int bit = 0; bit < 8; bit++) {
                if ((crc & 0x80000000L) != 0L) {
                    crc = ((crc << 1) ^ 0x04C11DB7L) & 0xFFFFFFFFL;
                } else {
                    crc = (crc << 1) & 0xFFFFFFFFL;
                }
            }
        }
        return (crc ^ 0xFFFFFFFFL) & 0xFFFFFFFFL;
    }

    public static String digestHex(String normalizedSeal) {
        long value = crc32(normalizedSeal.getBytes(StandardCharsets.UTF_8));
        return String.format(java.util.Locale.ROOT, "%08x", value);
    }
}
