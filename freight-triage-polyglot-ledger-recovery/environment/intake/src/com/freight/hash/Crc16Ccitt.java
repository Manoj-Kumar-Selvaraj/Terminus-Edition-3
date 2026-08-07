package com.freight.hash;

/** crc16_ccitt over raw bytes. */
public final class Crc16Ccitt implements HashAlgorithm {

    @Override
    public String name() {
        return "crc16_ccitt";
    }

    @Override
    public long apply(byte[] data) {
        long crc = 0xFFFFL;
        for (int i = 0; i < data.length; i++) {
            crc ^= ((long) (data[i] & 0xFF)) << 8;
            for (int bit = 0; bit < 8; bit++) {
                crc = ((crc & 0x8000L) != 0L) ? (((crc << 1) ^ 0x1021L) & 0xFFFFL)
                                              : ((crc << 1) & 0xFFFFL);
            }
        }
        return crc & 0xFFFFL;
    }
}
