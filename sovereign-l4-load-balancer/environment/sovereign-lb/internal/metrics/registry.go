package metrics

import (
	"fmt"
	"io"
	"sort"
	"strings"
	"sync"
)

type Registry struct { mutex sync.RWMutex; counters map[string]uint64; gauges map[string]int64 }
func New() *Registry { return &Registry{counters: map[string]uint64{}, gauges: map[string]int64{}} }
func key(name string, labels ...string) string { if len(labels) == 0 { return name }; return name+"{"+strings.Join(labels, ",")+"}" }
func (registry *Registry) Inc(name string, labels ...string) { registry.mutex.Lock(); defer registry.mutex.Unlock(); registry.counters[key(name, labels...)]++ }
func (registry *Registry) Set(name string, value int64, labels ...string) { registry.mutex.Lock(); defer registry.mutex.Unlock(); registry.gauges[key(name, labels...)] = value }
func (registry *Registry) WriteTo(writer io.Writer) {
	registry.mutex.RLock(); defer registry.mutex.RUnlock()
	keys := make([]string, 0, len(registry.counters)+len(registry.gauges)); for item := range registry.counters { keys = append(keys, item) }; for item := range registry.gauges { keys = append(keys, item) }; sort.Strings(keys)
	for _, item := range keys { if value, ok := registry.counters[item]; ok { fmt.Fprintf(writer, "%s %d\n", item, value) } else { fmt.Fprintf(writer, "%s %d\n", item, registry.gauges[item]) } }
}