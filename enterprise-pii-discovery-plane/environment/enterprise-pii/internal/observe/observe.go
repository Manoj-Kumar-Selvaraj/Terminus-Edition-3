package observe

import (
	"sort"
	"strings"
	"sync"
	"time"

	"enterprise-pii/internal/model"
)

type AuditLog struct { mu sync.Mutex; capacity int; next uint64; dropped uint64; events []model.AuditEvent }
func NewAudit(capacity int)*AuditLog{return &AuditLog{capacity:capacity,next:1}}
func (a *AuditLog) Append(event model.AuditEvent){a.mu.Lock();defer a.mu.Unlock();event.Sequence=a.next;a.next++;if event.At.IsZero(){event.At=time.Now().UTC()};if len(a.events)==a.capacity{copy(a.events,a.events[1:]);a.events=a.events[:a.capacity-1];a.dropped++};a.events=append(a.events,event)}
func (a *AuditLog) Snapshot()([]model.AuditEvent,uint64){a.mu.Lock();defer a.mu.Unlock();return append([]model.AuditEvent(nil),a.events...),a.dropped}
type Metrics struct{mu sync.Mutex;capacity int;series map[string]float64;dropped uint64}
func NewMetrics(capacity int)*Metrics{return &Metrics{capacity:capacity,series:map[string]float64{}}}
func metricKey(name string,labels map[string]string)string{keys:=make([]string,0,len(labels));for key:=range labels{keys=append(keys,key)};sort.Strings(keys);var parts=[]string{name};for _,key:=range keys{parts=append(parts,key+"="+labels[key])};return strings.Join(parts,";")}
func (m *Metrics) Add(name string,labels map[string]string,value float64){m.mu.Lock();defer m.mu.Unlock();key:=metricKey(name,labels);if _,ok:=m.series[key];!ok&&len(m.series)>=m.capacity{m.dropped++;return};m.series[key]+=value}
func (m *Metrics) Snapshot()(map[string]float64,uint64){m.mu.Lock();defer m.mu.Unlock();out:=map[string]float64{};for key,value:=range m.series{out[key]=value};return out,m.dropped}
type Readiness struct{Recovered bool `json:"recovered"`;RequiredSources int `json:"required_sources"`;AvailableSources int `json:"available_sources"`;RequiredWorkers int `json:"required_workers"`;CurrentWorkers int `json:"current_workers"`;Ready bool `json:"ready"`;Reasons []string `json:"reasons"`}
func Evaluate(recovered bool,sources []model.Source,available map[string]bool,workers []model.WorkerSession,requiredWorkers int,now time.Time)Readiness{result:=Readiness{Recovered:recovered,RequiredWorkers:requiredWorkers};for _,source:=range sources{if source.Required{result.RequiredSources++;if available[source.ID]{result.AvailableSources++}}};for _,worker:=range workers{if worker.ExpiresAt.After(now){result.CurrentWorkers++}};if !recovered{result.Reasons=append(result.Reasons,"recovery_incomplete")};if result.AvailableSources<result.RequiredSources{result.Reasons=append(result.Reasons,"required_source_unavailable")};if result.CurrentWorkers<requiredWorkers{result.Reasons=append(result.Reasons,"worker_capacity_unavailable")};result.Ready=len(result.Reasons)==0;return result}