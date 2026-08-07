package com.freight.format;

/** Formatter: kg to tonnes. */
public final class KgToTonnes implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "kg_to_tonnes";
    }

    @Override
    public String apply(long value) {
        boolean negative = value < 0L;
        long absolute = negative ? -value : value;
        return (negative ? "-" : "") + (absolute / 1000L) + "."
                + String.format(java.util.Locale.ROOT, "%03d", absolute % 1000L);
    }
}
