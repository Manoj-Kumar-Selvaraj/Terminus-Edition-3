package com.freight.hash;

/** crc32_ieee over raw bytes. */
public final class Crc32Ieee implements HashAlgorithm {

    @Override
    public String name() {
        return "crc32_ieee";
    }

    @Override
    public long apply(byte[] data) {
        long crc = 0xFFFFFFFFL;
        for (int i = 0; i < data.length; i++) {
            crc ^= (data[i] & 0xFF);
            for (int bit = 0; bit < 8; bit++) {
                crc = ((crc & 1L) != 0L) ? ((crc >>> 1) ^ 0xEDB88320L) : (crc >>> 1);
            }
        }
        return (crc ^ 0xFFFFFFFFL) & 0xFFFFFFFFL;
    }
}
