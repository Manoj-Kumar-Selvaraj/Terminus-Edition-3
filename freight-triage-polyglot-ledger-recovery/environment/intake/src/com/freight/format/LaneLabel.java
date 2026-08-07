package com.freight.format;

/** Formatter: lane label. */
public final class LaneLabel implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "lane_label";
    }

    @Override
    public String apply(long value) {
        long index = ((value % 1000L) + 1000L) % 1000L;
        return String.format(java.util.Locale.ROOT, "LN-%03d", index);
    }
}
