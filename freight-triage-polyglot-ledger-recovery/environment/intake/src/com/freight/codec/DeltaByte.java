package com.freight.codec;

/** delta_byte codec. */
public final class DeltaByte implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "delta_byte";
    }

    @Override
    public byte[] encode(byte[] data) {
        byte[] out = new byte[data.length];
        int previous = 0;
        for (int i = 0; i < data.length; i++) {
            int current = data[i] & 0xFF;
            out[i] = (byte) ((current - previous) & 0xFF);
            previous = current;
        }
        return out;
    }

    @Override
    public byte[] decode(byte[] data) {
        byte[] out = new byte[data.length];
        int previous = 0;
        for (int i = 0; i < data.length; i++) {
            int current = ((data[i] & 0xFF) + previous) & 0xFF;
            out[i] = (byte) current;
            previous = current;
        }
        return out;
    }
}
