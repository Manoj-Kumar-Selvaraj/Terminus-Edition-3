package com.freight.stats;

/** range_milli kernel. */
public final class RangeMilli implements StatKernel {

    @Override
    public String name() {
        return "range_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long low = series[0];
        long high = series[0];
        for (int i = 1; i < series.length; i++) {
            if (series[i] < low) {
                low = series[i];
            }
            if (series[i] > high) {
                high = series[i];
            }
        }
        return (high - low) * 1000L;
    }
}
