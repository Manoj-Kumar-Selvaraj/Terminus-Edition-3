package com.freight.stats;

/** variance_milli kernel. */
public final class VarianceMilli implements StatKernel {

    @Override
    public String name() {
        return "variance_milli";
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
            accumulator += delta * delta / 1000L;
        }
        return StatSupport.floorDiv(accumulator, count);
    }
}
