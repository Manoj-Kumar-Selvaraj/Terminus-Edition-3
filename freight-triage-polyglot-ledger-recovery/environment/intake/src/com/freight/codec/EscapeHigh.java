package com.freight.codec;

/** escape_high codec. */
public final class EscapeHigh implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "escape_high";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xFF;
            if (b == 0x1B) {
                out.write(0x1B);
                out.write(0x7F);
            } else if (b >= 0x80) {
                out.write(0x1B);
                out.write(b - 0x80);
            } else {
                out.write(b);
            }
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xFF;
            if (b != 0x1B) {
                out.write(b);
                continue;
            }
            if (i + 1 >= data.length) {
                break;
            }
            int next = data[++i] & 0xFF;
            out.write(next == 0x7F ? 0x1B : (next + 0x80) & 0xFF);
        }
        return out.toByteArray();
    }
}
