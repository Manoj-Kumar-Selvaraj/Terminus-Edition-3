package com.freight.hash;

/** elf_hash over raw bytes. */
public final class ElfHash implements HashAlgorithm {

    @Override
    public String name() {
        return "elf_hash";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0L;
        for (int i = 0; i < data.length; i++) {
            state = ((state << 4) + (data[i] & 0xFF)) & 0xFFFFFFFFL;
            long high = state & 0xF0000000L;
            if (high != 0L) {
                state ^= high >>> 24;
            }
            state &= (~high) & 0xFFFFFFFFL;
        }
        return state;
    }
}
