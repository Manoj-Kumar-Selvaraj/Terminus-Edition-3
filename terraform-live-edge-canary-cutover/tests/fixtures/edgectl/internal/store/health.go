package store

import "fmt"

// HealthyOriginCount returns how many origins in the pool currently report healthy.
func HealthyOriginCount(p Pool) int {
	n := 0
	for _, o := range p.Origins {
		if o.Healthy {
			n++
		}
	}
	return n
}

// EffectiveMinHealthy returns the floor used by canary and DNS guards.
// A configured min_healthy of 0 still requires at least one healthy origin
// before traffic may be shifted.
func EffectiveMinHealthy(p Pool) int {
	if p.MinHealthy < 1 {
		return 1
	}
	return p.MinHealthy
}

// DescribePoolHealth is a short diagnostic string used in conflict messages.
func DescribePoolHealth(p Pool) string {
	return fmt.Sprintf("pool %s healthy=%d/%d min=%d color=%s",
		p.ID, HealthyOriginCount(p), len(p.Origins), EffectiveMinHealthy(p), p.Color)
}
