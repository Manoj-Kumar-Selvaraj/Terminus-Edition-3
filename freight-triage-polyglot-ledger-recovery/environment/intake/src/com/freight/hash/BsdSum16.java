package com.freight.hash;

/** bsd_sum16 over raw bytes. */
public final class BsdSum16 implements HashAlgorithm {

    @Override
    public String name() {
        return "bsd_sum16";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0L;
        for (int i = 0; i < data.length; i++) {
            state = ((state >>> 1) | ((state & 1L) << 15)) & 0xFFFFL;
            state = (state + (data[i] & 0xFF)) & 0xFFFFL;
        }
        return state;
    }
}
