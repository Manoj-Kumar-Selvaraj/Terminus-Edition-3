package com.freight.codec;

/** run_length codec. */
public final class RunLength implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "run_length";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int index = 0;
        while (index < data.length) {
            byte value = data[index];
            int run = 1;
            while (index + run < data.length && data[index + run] == value && run < 255) {
                run++;
            }
            out.write(run);
            out.write(value & 0xFF);
            index += run;
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i + 1 < data.length; i += 2) {
            int run = data[i] & 0xFF;
            for (int k = 0; k < run; k++) {
                out.write(data[i + 1] & 0xFF);
            }
        }
        return out.toByteArray();
    }
}
