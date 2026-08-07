package com.freight.stats;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of statistics kernels. */
public final class StatRegistry {

    private StatRegistry() {
    }

    public static List<StatKernel> all() {
        List<StatKernel> registry = new ArrayList<StatKernel>();
        registry.add(new SumMilli());
        registry.add(new MeanMilli());
        registry.add(new MinMilli());
        registry.add(new MaxMilli());
        registry.add(new RangeMilli());
        registry.add(new VarianceMilli());
        registry.add(new StddevMilli());
        registry.add(new MedianMilli());
        registry.add(new P90Milli());
        registry.add(new EwmaMilli());
        registry.add(new CountMilli());
        registry.add(new AbsdevMilli());
        return Collections.unmodifiableList(registry);
    }
}
