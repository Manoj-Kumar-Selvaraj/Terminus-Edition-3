package com.freight.codec;

/** chunk16_framed codec. */
public final class Chunk16Framed implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "chunk16_framed";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int index = 0;
        while (index < data.length) {
            int take = Math.min(16, data.length - index);
            out.write(take);
            out.write(data, index, take);
            index += take;
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int index = 0;
        while (index < data.length) {
            int take = data[index] & 0xFF;
            index++;
            if (index + take > data.length) {
                take = data.length - index;
            }
            out.write(data, index, take);
            index += take;
        }
        return out.toByteArray();
    }
}
