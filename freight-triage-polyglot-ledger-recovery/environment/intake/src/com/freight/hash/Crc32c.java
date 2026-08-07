package com.freight.hash;

/** crc32c over raw bytes. */
public final class Crc32c implements HashAlgorithm {

    @Override
    public String name() {
        return "crc32c";
    }

    @Override
    public long apply(byte[] data) {
        long crc = 0xFFFFFFFFL;
        for (int i = 0; i < data.length; i++) {
            crc ^= (data[i] & 0xFF);
            for (int bit = 0; bit < 8; bit++) {
                crc = ((crc & 1L) != 0L) ? ((crc >>> 1) ^ 0x82F63B78L) : (crc >>> 1);
            }
        }
        return (crc ^ 0xFFFFFFFFL) & 0xFFFFFFFFL;
    }
}
