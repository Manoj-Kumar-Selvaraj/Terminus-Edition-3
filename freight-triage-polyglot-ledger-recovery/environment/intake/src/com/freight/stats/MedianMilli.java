package com.freight.stats;

/** median_milli kernel. */
public final class MedianMilli implements StatKernel {

    @Override
    public String name() {
        return "median_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long[] sorted = series.clone();
        java.util.Arrays.sort(sorted);
        int middle = sorted.length / 2;
        if (sorted.length % 2 == 1) {
            return sorted[middle] * 1000L;
        }
        return StatSupport.floorDiv((sorted[middle - 1] + sorted[middle]) * 1000L, 2L);
    }
}
