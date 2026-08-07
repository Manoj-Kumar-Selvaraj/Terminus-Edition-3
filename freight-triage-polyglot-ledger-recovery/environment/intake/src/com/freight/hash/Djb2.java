package com.freight.hash;

/** djb2 over raw bytes. */
public final class Djb2 implements HashAlgorithm {

    @Override
    public String name() {
        return "djb2";
    }

    @Override
    public long apply(byte[] data) {
        long state = 5381L;
        for (int i = 0; i < data.length; i++) {
            state = (state * 33L + (data[i] & 0xFF)) & 0xFFFFFFFFL;
        }
        return state;
    }
}
