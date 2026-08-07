package com.freight.hash;

/** crc8_atm over raw bytes. */
public final class Crc8Atm implements HashAlgorithm {

    @Override
    public String name() {
        return "crc8_atm";
    }

    @Override
    public long apply(byte[] data) {
        long crc = 0L;
        for (int i = 0; i < data.length; i++) {
            crc ^= (data[i] & 0xFF);
            for (int bit = 0; bit < 8; bit++) {
                crc = ((crc & 0x80L) != 0L) ? (((crc << 1) ^ 0x07L) & 0xFFL) : ((crc << 1) & 0xFFL);
            }
        }
        return crc & 0xFFL;
    }
}
