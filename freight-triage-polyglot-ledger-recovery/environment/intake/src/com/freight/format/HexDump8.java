package com.freight.format;

/** Formatter: hex dump8. */
public final class HexDump8 implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "hex_dump8";
    }

    @Override
    public String apply(long value) {
        long truncated = value & 0xFFFFFFFFL;
        return String.format(java.util.Locale.ROOT, "%08x", truncated);
    }
}
