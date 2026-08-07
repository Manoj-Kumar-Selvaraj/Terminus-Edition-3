package com.freight.stats;

/** count_milli kernel. */
public final class CountMilli implements StatKernel {

    @Override
    public String name() {
        return "count_milli";
    }

    @Override
    public long apply(long[] series) {
        return ((long) series.length) * 1000L;
    }
}
