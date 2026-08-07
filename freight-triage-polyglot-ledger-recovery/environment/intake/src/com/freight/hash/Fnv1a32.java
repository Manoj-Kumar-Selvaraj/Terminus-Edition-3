package com.freight.hash;

/** fnv1a32 over raw bytes. */
public final class Fnv1a32 implements HashAlgorithm {

    @Override
    public String name() {
        return "fnv1a32";
    }

    @Override
    public long apply(byte[] data) {
        long state = 2166136261L;
        for (int i = 0; i < data.length; i++) {
            state ^= (data[i] & 0xFF);
            state = (state * 16777619L) & 0xFFFFFFFFL;
        }
        return state;
    }
}
