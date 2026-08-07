package com.freight.format;

/** Formatter: cents to amount. */
public final class CentsToAmount implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "cents_to_amount";
    }

    @Override
    public String apply(long value) {
        boolean negative = value < 0L;
        long absolute = negative ? -value : value;
        return (negative ? "-" : "") + (absolute / 100L) + "."
                + String.format(java.util.Locale.ROOT, "%02d", absolute % 100L);
    }
}
