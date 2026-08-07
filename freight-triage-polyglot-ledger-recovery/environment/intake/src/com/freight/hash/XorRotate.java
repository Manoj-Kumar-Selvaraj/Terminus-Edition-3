package com.freight.hash;

/** xor_rotate over raw bytes. */
public final class XorRotate implements HashAlgorithm {

    @Override
    public String name() {
        return "xor_rotate";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0L;
        for (int i = 0; i < data.length; i++) {
            state = (((state << 5) | (state >>> 27)) ^ (data[i] & 0xFF)) & 0xFFFFFFFFL;
        }
        return state;
    }
}
