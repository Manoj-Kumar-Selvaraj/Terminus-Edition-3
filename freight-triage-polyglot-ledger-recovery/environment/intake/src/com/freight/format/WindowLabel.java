package com.freight.format;

/** Formatter: window label. */
public final class WindowLabel implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "window_label";
    }

    @Override
    public String apply(long value) {
        long index = ((value % 1000000L) + 1000000L) % 1000000L;
        return String.format(java.util.Locale.ROOT, "W-%06d", index);
    }
}
