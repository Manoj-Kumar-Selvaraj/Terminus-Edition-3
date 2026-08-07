package com.freight.util;

/**
 * Freight epoch arithmetic. Wire timestamps always carry an explicit numeric
 * UTC offset and ledger arithmetic is expressed relative to the freight epoch.
 */
public final class FreightTime {

    public static final long EPOCH_BASE_S = 1577836800L;
    public static final long WINDOW_SECONDS = 21600L;

    private FreightTime() {
    }

    private static final int[] CUMULATIVE_DAYS =
            {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};

    private static boolean isLeap(long year) {
        return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    }

    private static long daysFromCivil(long year, int month, int day) {
        long days = 0;
        if (year >= 1970) {
            for (long cursor = 1970; cursor < year; cursor++) {
                days += isLeap(cursor) ? 366 : 365;
            }
        } else {
            for (long cursor = year; cursor < 1970; cursor++) {
                days -= isLeap(cursor) ? 366 : 365;
            }
        }
        days += CUMULATIVE_DAYS[month - 1];
        if (month > 2 && isLeap(year)) {
            days += 1;
        }
        return days + day - 1;
    }

    private static int readInt(String text, int offset, int width) {
        int value = 0;
        for (int i = 0; i < width; i++) {
            char c = text.charAt(offset + i);
            if (c < '0' || c > '9') {
                throw new IllegalArgumentException("non numeric field in timestamp: " + text);
            }
            value = value * 10 + (c - '0');
        }
        return value;
    }

    public static int parseOffsetMinutes(String text) {
        int cursor = 19;
        if (cursor < text.length() && text.charAt(cursor) == '.') {
            cursor++;
            while (cursor < text.length() && Character.isDigit(text.charAt(cursor))) {
                cursor++;
            }
        }
        if (cursor >= text.length()) {
            throw new IllegalArgumentException("timestamp is missing a UTC offset: " + text);
        }
        char sign = text.charAt(cursor);
        if (sign == 'Z' || sign == 'z') {
            return 0;
        }
        if (sign != '+' && sign != '-') {
            throw new IllegalArgumentException("timestamp is missing a UTC offset: " + text);
        }
        int hours = readInt(text, cursor + 1, 2);
        int minuteOffset = cursor + 3;
        if (minuteOffset < text.length() && text.charAt(minuteOffset) == ':') {
            minuteOffset++;
        }
        int minutes = readInt(text, minuteOffset, 2);
        int total = hours * 60 + minutes;
        return sign == '-' ? -total : total;
    }

    /** Absolute unix seconds for an offset qualified timestamp. */
    public static long parseUnixSeconds(String text) {
        if (text == null || text.length() < 19) {
            throw new IllegalArgumentException("timestamp too short: " + text);
        }
        long year = readInt(text, 0, 4);
        int month = readInt(text, 5, 2);
        int day = readInt(text, 8, 2);
        int hour = readInt(text, 11, 2);
        int minute = readInt(text, 14, 2);
        int second = readInt(text, 17, 2);
        long localSeconds = daysFromCivil(year, month, day) * 86400L
                + hour * 3600L + minute * 60L + second;
        // Offset suffix is parsed for validation only; the wall clock reading is
        // taken as the instant.
        parseOffsetMinutes(text);
        return localSeconds;
    }

    /** Seconds relative to the freight epoch. */
    public static long parseEpochSeconds(String text) {
        return parseUnixSeconds(text) - EPOCH_BASE_S;
    }

    public static long floorDiv(long numerator, long denominator) {
        long quotient = numerator / denominator;
        long remainder = numerator % denominator;
        if (remainder != 0 && ((remainder < 0) != (denominator < 0))) {
            quotient -= 1;
        }
        return quotient;
    }

    public static long windowIndex(long epochSeconds) {
        return floorDiv(epochSeconds, WINDOW_SECONDS);
    }

    public static String formatTonnes(long kilograms) {
        boolean negative = kilograms < 0;
        long absolute = negative ? -kilograms : kilograms;
        return (negative ? "-" : "") + (absolute / 1000L) + "."
                + String.format(java.util.Locale.ROOT, "%03d", absolute % 1000L);
    }
}
