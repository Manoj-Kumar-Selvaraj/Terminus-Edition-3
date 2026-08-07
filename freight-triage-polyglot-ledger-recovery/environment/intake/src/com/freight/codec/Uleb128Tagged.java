package com.freight.codec;

/** uleb128_tagged codec. */
public final class Uleb128Tagged implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "uleb128_tagged";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i < data.length; i++) {
            int raw = data[i] & 0xFF;
            int value = (raw << 3) | (raw & 7);
            while (value >= 0x80) {
                out.write((value & 0x7F) | 0x80);
                value >>>= 7;
            }
            out.write(value);
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int value = 0;
        int shift = 0;
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xFF;
            value |= (b & 0x7F) << shift;
            if ((b & 0x80) != 0) {
                shift += 7;
                continue;
            }
            out.write((value >>> 3) & 0xFF);
            value = 0;
            shift = 0;
        }
        return out.toByteArray();
    }
}
