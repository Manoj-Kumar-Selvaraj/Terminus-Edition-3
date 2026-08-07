package com.freight.stats;

/** p90_milli kernel. */
public final class P90Milli implements StatKernel {

    @Override
    public String name() {
        return "p90_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long[] sorted = series.clone();
        java.util.Arrays.sort(sorted);
        long count = sorted.length;
        long rank = (9L * count + 9L) / 10L;
        if (rank < 1L) {
            rank = 1L;
        }
        if (rank > count) {
            rank = count;
        }
        return sorted[(int) (rank - 1L)] * 1000L;
    }
}
