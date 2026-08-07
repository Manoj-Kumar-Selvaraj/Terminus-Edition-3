package com.freight.stats;

/** absdev_milli kernel. */
public final class AbsdevMilli implements StatKernel {

    @Override
    public String name() {
        return "absdev_milli";
    }

    @Override
    public long apply(long[] series) {
        if (series.length == 0) {
            return 0L;
        }
        long count = series.length;
        long total = 0L;
        for (int i = 0; i < series.length; i++) {
            total += series[i];
        }
        long mean = StatSupport.floorDiv(total * 1000L, count);
        long accumulator = 0L;
        for (int i = 0; i < series.length; i++) {
            long delta = series[i] * 1000L - mean;
            accumulator += delta < 0L ? -delta : delta;
        }
        return StatSupport.floorDiv(accumulator, count);
    }
}
