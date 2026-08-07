package com.freight.stats;

/** ewma_milli kernel. */
public final class EwmaMilli implements StatKernel {

    @Override
    public String name() {
        return "ewma_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long state = series[0] * 1000L;
        for (int i = 1; i < series.length; i++) {
            state += StatSupport.floorDiv(series[i] * 1000L - state, 4L);
        }
        return state;
    }
}
