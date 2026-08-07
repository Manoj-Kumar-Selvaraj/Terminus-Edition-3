package com.freight.codec;

/** quoted_freight codec. */
public final class QuotedFreight implements Codec {

    private static final String HEX_DIGITS = "0123456789abcdef";
    private static final String UPPER_HEX = "0123456789ABCDEF";
    private static final String BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    private static final String BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    @Override
    public String name() {
        return "quoted_freight";
    }

    @Override
    public byte[] encode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i < data.length; i++) {
            int b = data[i] & 0xFF;
            if (b >= 0x20 && b <= 0x7E && b != '=') {
                out.write(b);
                continue;
            }
            out.write('=');
            out.write(UPPER_HEX.charAt(b >>> 4));
            out.write(UPPER_HEX.charAt(b & 0x0F));
        }
        return out.toByteArray();
    }

    @Override
    public byte[] decode(byte[] data) {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        for (int i = 0; i < data.length; i++) {
            if ((data[i] & 0xFF) != '=') {
                out.write(data[i] & 0xFF);
                continue;
            }
            if (i + 2 >= data.length) {
                break;
            }
            int high = CodecSupport.hexValue((char) (data[i + 1] & 0xFF));
            int low = CodecSupport.hexValue((char) (data[i + 2] & 0xFF));
            if (high < 0 || low < 0) {
                return new byte[0];
            }
            out.write((high << 4) | low);
            i += 2;
        }
        return out.toByteArray();
    }
}
