package com.freight.format;

/** Formatter: thousands group. */
public final class ThousandsGroup implements Formatter {

    private static final String BASE36_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    @Override
    public String name() {
        return "thousands_group";
    }

    @Override
    public String apply(long value) {
        boolean negative = value < 0L;
        long absolute = negative ? -value : value;
        String digits = Long.toString(absolute);
        StringBuilder grouped = new StringBuilder();
        int count = 0;
        for (int i = digits.length() - 1; i >= 0; i--) {
            grouped.append(digits.charAt(i));
            count++;
            if (count % 3 == 0 && i > 0) {
                grouped.append(',');
            }
        }
        grouped.reverse();
        return (negative ? "-" : "") + grouped;
    }
}
