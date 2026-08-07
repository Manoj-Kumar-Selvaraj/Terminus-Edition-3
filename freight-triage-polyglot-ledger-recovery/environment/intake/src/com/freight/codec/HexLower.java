package com.freight.codec;

/** hex_lower codec. */
public final class HexLower implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "hex_lower";
    }

    @Override
    public byte[] encode(byte[] data) {
        byte[] out = new byte[data.length * 2];
        for (int i = 0; i < data.length; i++) {
            int value = data[i] & 0xFF;
            out[i * 2] = (byte) HEX_DIGITS.charAt(value >>> 4);
            out[i * 2 + 1] = (byte) HEX_DIGITS.charAt(value & 0x0F);
        }
        return out;
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i + 1 < data.length; i += 2) {
            int high = CodecSupport.hexValue((char) (data[i] & 0xFF));
            int low = CodecSupport.hexValue((char) (data[i + 1] & 0xFF));
            if (high < 0 || low < 0) {
                return new byte[0];
            }
            out.write((high << 4) | low);
        }
        return out.toByteArray();
    }
}
