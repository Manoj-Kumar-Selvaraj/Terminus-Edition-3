package com.freight.stats;

/** sum_milli kernel. */
public final class SumMilli implements StatKernel {

    @Override
    public String name() {
        return "sum_milli";
    }

    @Override
    public long apply(long[] series) {
        long total = 0L;
        for (int i = 0; i < series.length; i++) {
            total += series[i];
        }
        return total * 1000L;
    }
}
