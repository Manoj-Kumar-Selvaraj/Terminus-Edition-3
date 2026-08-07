package com.freight.stats;

/** stddev_milli kernel. */
public final class StddevMilli implements StatKernel {

    @Override
    public String name() {
        return "stddev_milli";
    }

    @Override
    public long apply(long[] series) {
        long variance = new VarianceMilli().apply(series);
        return StatSupport.integerSqrt(variance * 1000L);
    }
}
