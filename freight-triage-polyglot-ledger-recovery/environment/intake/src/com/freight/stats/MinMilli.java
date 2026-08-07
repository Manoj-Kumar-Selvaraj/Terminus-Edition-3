package com.freight.stats;

/** min_milli kernel. */
public final class MinMilli implements StatKernel {

    @Override
    public String name() {
        return "min_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long best = series[0];
        for (int i = 1; i < series.length; i++) {
            if (series[i] < best) {
                best = series[i];
            }
        }
        return best * 1000L;
    }
}
