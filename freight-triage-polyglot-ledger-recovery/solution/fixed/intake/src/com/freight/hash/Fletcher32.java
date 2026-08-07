package com.freight.hash;

/** fletcher32 over raw bytes. */
public final class Fletcher32 implements HashAlgorithm {

    @Override
    public String name() {
        return "fletcher32";
    }

    @Override
    public long apply(byte[] data) {
        long low = 0L;
        long high = 0L;
        for (int i = 0; i < data.length; i += 2) {
            long word = (data[i] & 0xFF);
            if (i + 1 < data.length) {
                word |= ((long) (data[i + 1] & 0xFF)) << 8;
            }
            low = (low + word) % 65535L;
            high = (high + low) % 65535L;
        }
        return ((high << 16) | low) & 0xFFFFFFFFL;
    }
}
