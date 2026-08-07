package com.freight.format;

/** Formatter: slot label. */
public final class SlotLabel implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "slot_label";
    }

    @Override
    public String apply(long value) {
        if (value <= 0L) {
            return "S--";
        }
        return String.format(java.util.Locale.ROOT, "S%02d", value % 100L);
    }
}
