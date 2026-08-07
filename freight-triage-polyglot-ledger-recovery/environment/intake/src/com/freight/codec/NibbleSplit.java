package com.freight.codec;

/** nibble_split codec. */
public final class NibbleSplit implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "nibble_split";
    }

    @Override
    public byte[] encode(byte[] data) {
        byte[] out = new byte[data.length * 2];
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xFF;
            out[i * 2] = (byte) ('A' + (b >>> 4));
            out[i * 2 + 1] = (byte) ('a' + (b & 0x0F));
        }
        return out;
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i + 1 < data.length; i += 2) {
            int high = (data[i] & 0xFF) - 'A';
            int low = (data[i + 1] & 0xFF) - 'a';
            out.write(((high << 4) | (low & 0x0F)) & 0xFF);
        }
        return out.toByteArray();
    }
}
