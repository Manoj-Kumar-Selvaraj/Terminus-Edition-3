package com.freight.format;

/** Formatter: sign prefix. */
public final class SignPrefix implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "sign_prefix";
    }

    @Override
    public String apply(long value) {
        if (value == 0L) {
            return "0";
        }
        if (value > 0L) {
            return "+" + value;
        }
        return Long.toString(value);
    }
}
