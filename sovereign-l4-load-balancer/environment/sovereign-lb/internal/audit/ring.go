package audit

import (
	"sync"
	"time"
)

type Event struct { At time.Time `json:"at"`; Actor string `json:"actor"`; Operation string `json:"operation"`; DigestPrefix string `json:"digest_prefix,omitempty"`; Revision uint64 `json:"revision,omitempty"`; Generation uint64 `json:"generation,omitempty"`; Outcome string `json:"outcome"`; Reason string `json:"reason,omitempty"` }
type Ring struct { mutex sync.RWMutex; events []Event; next int; full bool; dropped uint64 }

func New(capacity int) *Ring { if capacity < 1 { capacity = 1 }; return &Ring{events: make([]Event, capacity)} }
func (ring *Ring) Add(event Event) { ring.mutex.Lock(); defer ring.mutex.Unlock(); event.At = event.At.UTC(); if ring.full { ring.dropped++ }; ring.events[ring.next] = event; ring.next = (ring.next+1)%len(ring.events); ring.full = ring.full || ring.next == 0 }
func (ring *Ring) Snapshot() ([]Event, uint64) { ring.mutex.RLock(); defer ring.mutex.RUnlock(); count := ring.next; start := 0; if ring.full { count = len(ring.events); start = ring.next }; result := make([]Event, 0, count); for index := 0; index < count; index++ { result = append(result, ring.events[(start+index)%len(ring.events)]) }; return result, ring.dropped }