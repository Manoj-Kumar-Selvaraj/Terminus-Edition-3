package com.freight.format;

/** Formatter: ordinal suffix. */
public final class OrdinalSuffix implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "ordinal_suffix";
    }

    @Override
    public String apply(long value) {
        long mod100 = ((value % 100L) + 100L) % 100L;
        long mod10 = mod100 % 10L;
        String suffix = "th";
        if (mod100 < 11L || mod100 > 13L) {
            if (mod10 == 1L) {
                suffix = "st";
            } else if (mod10 == 2L) {
                suffix = "nd";
            } else if (mod10 == 3L) {
                suffix = "rd";
            }
        }
        return Long.toString(value) + suffix;
    }
}
