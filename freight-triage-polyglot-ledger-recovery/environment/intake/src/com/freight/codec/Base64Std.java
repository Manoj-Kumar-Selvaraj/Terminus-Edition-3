package com.freight.codec;

/** base64_std codec. */
public final class Base64Std implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "base64_std";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int index = 0;
        while (index < data.length) {
            int take = Math.min(3, data.length - index);
            int buffer = 0;
            for (int i = 0; i < 3; i++) {
                buffer <<= 8;
                if (i < take) {
                    buffer |= (data[index + i] & 0xFF);
                }
            }
            index += take;
            int emit = take + 1;
            for (int i = 0; i < 4; i++) {
                if (i < emit) {
                    out.write(BASE64_ALPHABET.charAt((buffer >>> (18 - 6 * i)) & 0x3F));
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
        int buffer = 0;
        int bits = 0;
        for (int i = 0; i < data.length; i++) {
            char c = (char) (data[i] & 0xFF);
            if (c == '=') {
                continue;
            }
            int value = CodecSupport.base64Value(c);
            if (value < 0) {
                return new byte[0];
            }
            buffer = (buffer << 6) | value;
            bits += 6;
            if (bits >= 8) {
                bits -= 8;
                out.write((buffer >>> bits) & 0xFF);
            }
        }
        return out.toByteArray();
    }
}
