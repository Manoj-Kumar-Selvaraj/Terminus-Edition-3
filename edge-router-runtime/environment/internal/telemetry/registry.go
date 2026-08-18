package telemetry

import (
	"bytes"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Counter struct {
	Name      string            `json:"name"`
	Labels    map[string]string `json:"labels"`
	Value     uint64            `json:"value"`
	UpdatedAt time.Time         `json:"updated_at"`
	Owner     string            `json:"owner"`
}

type Gauge struct {
	Name      string            `json:"name"`
	Labels    map[string]string `json:"labels"`
	Value     float64           `json:"value"`
	UpdatedAt time.Time         `json:"updated_at"`
	Owner     string            `json:"owner"`
}

type Registry struct {
	mu       sync.RWMutex
	counters map[string]*Counter
	gauges   map[string]*Gauge
	owners   map[string]map[string]struct{}
}

func New() *Registry {
	return &Registry{
		counters: make(map[string]*Counter),
		gauges:   make(map[string]*Gauge),
		owners:   make(map[string]map[string]struct{}),
	}
}

func metricKey(name string, labels map[string]string) string {
	keys := make([]string, 0, len(labels))
	for key := range labels {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	var builder strings.Builder
	builder.WriteString(name)
	for _, key := range keys {
		builder.WriteByte('|')
		builder.WriteString(key)
		builder.WriteByte('=')
		builder.WriteString(labels[key])
	}
	return builder.String()
}

func cloneLabels(labels map[string]string) map[string]string {
	out := make(map[string]string, len(labels))
	for key, value := range labels {
		out[key] = value
	}
	return out
}

func (r *Registry) Add(owner, name string, labels map[string]string, delta uint64) {
	key := metricKey(name, labels)
	r.mu.Lock()
	defer r.mu.Unlock()
	counter := r.counters[key]
	if counter == nil {
		counter = &Counter{Name: name, Labels: cloneLabels(labels), Owner: owner}
		r.counters[key] = counter
	}
	counter.Value += delta
	counter.UpdatedAt = time.Now().UTC()
	r.trackOwner(owner, key)
}

func (r *Registry) Set(owner, name string, labels map[string]string, value float64) {
	key := metricKey(name, labels)
	r.mu.Lock()
	defer r.mu.Unlock()
	gauge := r.gauges[key]
	if gauge == nil {
		gauge = &Gauge{Name: name, Labels: cloneLabels(labels), Owner: owner}
		r.gauges[key] = gauge
	}
	gauge.Value = value
	gauge.UpdatedAt = time.Now().UTC()
	r.trackOwner(owner, key)
}

func (r *Registry) trackOwner(owner, key string) {
	if owner == "" {
		owner = "process"
	}
	keys := r.owners[owner]
	if keys == nil {
		keys = make(map[string]struct{})
		r.owners[owner] = keys
	}
	keys[key] = struct{}{}
}

func (r *Registry) RetireOwner(owner string) int {
	r.mu.Lock()
	defer r.mu.Unlock()
	keys := r.owners[owner]
	if len(keys) == 0 {
		return 0
	}
	removed := 0
	for key := range keys {
		if _, exists := r.counters[key]; exists {
			removed++
		}
		if _, exists := r.gauges[key]; exists {
			removed++
		}
	}
	delete(r.owners, owner)
	return removed
}

func (r *Registry) Snapshot() ([]Counter, []Gauge) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	counters := make([]Counter, 0, len(r.counters))
	for _, value := range r.counters {
		copyValue := *value
		copyValue.Labels = cloneLabels(value.Labels)
		counters = append(counters, copyValue)
	}
	gauges := make([]Gauge, 0, len(r.gauges))
	for _, value := range r.gauges {
		copyValue := *value
		copyValue.Labels = cloneLabels(value.Labels)
		gauges = append(gauges, copyValue)
	}
	sort.Slice(counters, func(i, j int) bool {
		return metricKey(counters[i].Name, counters[i].Labels) < metricKey(counters[j].Name, counters[j].Labels)
	})
	sort.Slice(gauges, func(i, j int) bool {
		return metricKey(gauges[i].Name, gauges[i].Labels) < metricKey(gauges[j].Name, gauges[j].Labels)
	})
	return counters, gauges
}

func (r *Registry) Prometheus() []byte {
	counters, gauges := r.Snapshot()
	var buffer bytes.Buffer
	for _, counter := range counters {
		writeMetric(&buffer, counter.Name, counter.Labels, strconv.FormatUint(counter.Value, 10))
	}
	for _, gauge := range gauges {
		writeMetric(&buffer, gauge.Name, gauge.Labels, strconv.FormatFloat(gauge.Value, 'f', -1, 64))
	}
	return buffer.Bytes()
}

func writeMetric(buffer *bytes.Buffer, name string, labels map[string]string, value string) {
	buffer.WriteString(sanitize(name))
	if len(labels) > 0 {
		keys := make([]string, 0, len(labels))
		for key := range labels {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		buffer.WriteByte('{')
		for index, key := range keys {
			if index > 0 {
				buffer.WriteByte(',')
			}
			buffer.WriteString(sanitize(key))
			buffer.WriteString("=\"")
			buffer.WriteString(strings.ReplaceAll(labels[key], "\"", "\\\""))
			buffer.WriteByte('"')
		}
		buffer.WriteByte('}')
	}
	buffer.WriteByte(' ')
	buffer.WriteString(value)
	buffer.WriteByte('\n')
}

func sanitize(value string) string {
	value = strings.ReplaceAll(value, "-", "_")
	value = strings.ReplaceAll(value, ".", "_")
	if value == "" {
		return "edge_router_metric"
	}
	return value
}

func (r *Registry) Cardinality() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.counters) + len(r.gauges)
}

func (r *Registry) OwnerCardinality(owner string) int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.owners[owner])
}

func GenerationOwner(generation uint64) string {
	return fmt.Sprintf("generation:%d", generation)
}

func EndpointOwner(poolID, identity string, incarnation uint64) string {
	return fmt.Sprintf("endpoint:%s:%s:%d", poolID, identity, incarnation)
}
