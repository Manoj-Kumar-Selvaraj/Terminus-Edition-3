package com.freight.stats;

/** Integer helpers shared by the statistics kernels. */
public final class StatSupport {

    private StatSupport() {
    }

    public static long floorDiv(long numerator, long denominator) {
        if (denominator == 0L) {
            return 0L;
        }
        long quotient = numerator / denominator;
        long remainder = numerator % denominator;
        if (remainder != 0L && ((remainder < 0L) != (denominator < 0L))) {
            quotient -= 1L;
        }
        return quotient;
    }

    public static long integerSqrt(long value) {
        if (value <= 0L) {
            return 0L;
        }
        long low = 0L;
        long high = Math.min(value, 3037000499L);
        while (low < high) {
            long mid = low + (high - low + 1L) / 2L;
            if (mid <= value / mid) {
                low = mid;
            } else {
                high = mid - 1L;
            }
        }
        return low;
    }
}
