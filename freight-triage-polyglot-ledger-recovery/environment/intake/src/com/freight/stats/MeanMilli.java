package com.freight.stats;

/** mean_milli kernel. */
public final class MeanMilli implements StatKernel {

    @Override
    public String name() {
        return "mean_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long total = 0L;
        for (int i = 0; i < series.length; i++) {
            total += series[i];
        }
        return StatSupport.floorDiv(total * 1000L, series.length);
    }
}
