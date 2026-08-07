package com.freight.format;

/** Formatter: duration hms. */
public final class DurationHms implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "duration_hms";
    }

    @Override
    public String apply(long value) {
        boolean negative = value < 0L;
        long absolute = negative ? -value : value;
        return (negative ? "-" : "") + String.format(java.util.Locale.ROOT, "%02d:%02d:%02d",
                absolute / 3600L, (absolute / 60L) % 60L, absolute % 60L);
    }
}
