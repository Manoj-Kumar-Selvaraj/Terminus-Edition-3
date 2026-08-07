package com.freight.hash;

/** adler32 over raw bytes. */
public final class Adler32 implements HashAlgorithm {

    @Override
    public String name() {
        return "adler32";
    }

    @Override
    public long apply(byte[] data) {
        long low = 1L;
        long high = 0L;
        for (int i = 0; i < data.length; i++) {
            low = (low + (data[i] & 0xFF)) % 65521L;
            high = (high + low) % 65521L;
        }
        return ((high << 16) | low) & 0xFFFFFFFFL;
    }
}
