package com.freight.stats;

/** Fixed point windowed statistic scaled by one thousand. */
public interface StatKernel {

    String name();

    long apply(long[] series);

}
