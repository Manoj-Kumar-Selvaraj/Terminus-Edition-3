package com.freight.hash;

/** sdbm over raw bytes. */
public final class Sdbm implements HashAlgorithm {

    @Override
    public String name() {
        return "sdbm";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0L;
        for (int i = 0; i < data.length; i++) {
            state = ((data[i] & 0xFF) + (state << 6) + (state << 16) - state) & 0xFFFFFFFFL;
        }
        return state;
    }
}
