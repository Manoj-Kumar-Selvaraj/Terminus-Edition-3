package statx

// Registry lists every statistics kernel in catalogue order.
func Registry() []Kernel {
	return []Kernel{
		{Name: "sum_milli", Apply: SumMilli},
		{Name: "mean_milli", Apply: MeanMilli},
		{Name: "min_milli", Apply: MinMilli},
		{Name: "max_milli", Apply: MaxMilli},
		{Name: "range_milli", Apply: RangeMilli},
		{Name: "variance_milli", Apply: VarianceMilli},
		{Name: "stddev_milli", Apply: StddevMilli},
		{Name: "median_milli", Apply: MedianMilli},
		{Name: "p90_milli", Apply: P90Milli},
		{Name: "ewma_milli", Apply: EwmaMilli},
		{Name: "count_milli", Apply: CountMilli},
		{Name: "absdev_milli", Apply: AbsdevMilli},
	}
}
