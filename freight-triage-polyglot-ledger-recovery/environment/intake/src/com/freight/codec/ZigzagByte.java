package com.freight.codec;

/** zigzag_byte codec. */
public final class ZigzagByte implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "zigzag_byte";
    }

    @Override
    public byte[] encode(byte[] data) {
        byte[] out = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            int value = data[i];
            out[i] = (byte) (((value << 1) ^ (value >> 7)) & 0xFF);
        }
        return out;
    }

    @Override
    public byte[] decode(byte[] data) {
        byte[] out = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            int encoded = data[i] & 0xFF;
            out[i] = (byte) (((encoded >>> 1) ^ (-(encoded & 1))) & 0xFF);
        }
        return out;
    }
}
