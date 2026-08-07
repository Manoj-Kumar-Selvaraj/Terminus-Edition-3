package com.freight.codec;

/** base32_rfc4648 codec. */
public final class Base32Rfc4648 implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "base32_rfc4648";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int index = 0;
        int[] emitted = {0, 2, 4, 5, 7, 8};
        while (index < data.length) {
            int take = Math.min(5, data.length - index);
            long buffer = 0L;
            for (int i = 0; i < 5; i++) {
                buffer = (buffer << 8) | (i < take ? (data[index + i] & 0xFF) : 0);
            }
            index += take;
            int emit = emitted[take];
            for (int i = 0; i < 8; i++) {
                if (i < emit) {
                    out.write(BASE32_ALPHABET.charAt((int) ((buffer >>> (35 - 5 * i)) & 0x1FL)));
                } else {
                    out.write('=');
                }
            }
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        long buffer = 0L;
        int bits = 0;
        for (int i = 0; i < data.length; i++) {
            char c = (char) (data[i] & 0xFF);
            if (c == '=') {
                continue;
            }
            int value = CodecSupport.base32Value(c);
            if (value < 0) {
                return new byte[0];
            }
            buffer = (buffer << 5) | value;
            bits += 5;
            if (bits >= 8) {
                bits -= 8;
                out.write((int) ((buffer >>> bits) & 0xFFL));
            }
        }
        return out.toByteArray();
    }
}
