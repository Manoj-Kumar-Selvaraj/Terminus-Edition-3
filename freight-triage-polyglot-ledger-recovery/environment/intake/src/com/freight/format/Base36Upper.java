package com.freight.format;

/** Formatter: base36 upper. */
public final class Base36Upper implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "base36_upper";
    }

    @Override
    public String apply(long value) {
        if (value == 0L) {
            return "0";
        }
        boolean negative = value < 0L;
        long absolute = negative ? -value : value;
        StringBuilder out = new StringBuilder();
        while (absolute > 0L) {
            out.append(BASE36_DIGITS.charAt((int) (absolute % 36L)));
            absolute /= 36L;
        }
        out.reverse();
        return (negative ? "-" : "") + out;
    }
}
