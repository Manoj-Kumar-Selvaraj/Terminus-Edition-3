package com.freight.codec;

/** xor_pad8 codec. */
public final class XorPad8 implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "xor_pad8";
    }

    @Override
    public byte[] encode(byte[] data) {
        byte[] out = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            out[i] = (byte) ((data[i] & 0xFF) ^ CodecSupport.XOR_PAD[i % 8]);
        }
        return out;
    }

    @Override
    public byte[] decode(byte[] data) {
        byte[] out = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            out[i] = (byte) ((data[i] & 0xFF) ^ CodecSupport.XOR_PAD[i % 8]);
        }
        return out;
    }
}
