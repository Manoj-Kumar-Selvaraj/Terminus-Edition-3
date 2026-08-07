package com.freight.hash;

/** fletcher16 over raw bytes. */
public final class Fletcher16 implements HashAlgorithm {

    @Override
    public String name() {
        return "fletcher16";
    }

    @Override
    public long apply(byte[] data) {
        long low = 0L;
        long high = 0L;
        for (int i = 0; i < data.length; i++) {
            low = (low + (data[i] & 0xFF)) % 255L;
            high = (high + low) % 255L;
        }
        return ((high << 8) | low) & 0xFFFFL;
    }
}
