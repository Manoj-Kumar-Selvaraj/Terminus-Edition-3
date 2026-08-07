package com.freight.hash;

/** fnv1a64 over raw bytes. */
public final class Fnv1a64 implements HashAlgorithm {

    @Override
    public String name() {
        return "fnv1a64";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0xCBF29CE484222325L;
        for (int i = 0; i < data.length; i++) {
            state ^= (data[i] & 0xFF);
            state *= 0x100000001B3L;
        }
        return state;
    }
}
