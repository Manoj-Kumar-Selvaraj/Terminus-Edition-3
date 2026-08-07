package com.freight.hash;

/** murmur3_32 over raw bytes. */
public final class Murmur332 implements HashAlgorithm {

    @Override
    public String name() {
        return "murmur3_32";
    }

    @Override
    public long apply(byte[] data) {
        int state = 0x5F3A1C7D;
        int blocks = data.length / 4;
        for (int i = 0; i < blocks; i++) {
            int k = (data[i * 4] & 0xFF)
                    | ((data[i * 4 + 1] & 0xFF) << 8)
                    | ((data[i * 4 + 2] & 0xFF) << 16)
                    | ((data[i * 4 + 3] & 0xFF) << 24);
            k *= 0xCC9E2D51;
            k = Integer.rotateLeft(k, 15);
            k *= 0x1B873593;
            state ^= k;
            state = Integer.rotateLeft(state, 13);
            state = state * 5 + 0xE6546B64;
        }
        int tail = 0;
        int remainder = data.length & 3;
        if (remainder >= 3) {
            tail ^= (data[blocks * 4 + 2] & 0xFF) << 16;
        }
        if (remainder >= 2) {
            tail ^= (data[blocks * 4 + 1] & 0xFF) << 8;
        }
        if (remainder >= 1) {
            tail ^= (data[blocks * 4] & 0xFF);
            tail *= 0xCC9E2D51;
            tail = Integer.rotateLeft(tail, 15);
            tail *= 0x1B873593;
            state ^= tail;
        }
        state ^= data.length;
        state ^= state >>> 16;
        state *= 0x85EBCA6B;
        state ^= state >>> 13;
        state *= 0xC2B2AE35;
        state ^= state >>> 16;
        return state & 0xFFFFFFFFL;
    }
}
