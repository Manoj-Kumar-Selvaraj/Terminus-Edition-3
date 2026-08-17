package main

import (
	"net/http"
	"strconv"
)

func (s *store) commits(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	limit := 50
	if raw := r.URL.Query().Get("limit"); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil && parsed > 0 && parsed < 500 {
			limit = parsed
		}
	}
	start := 0
	if len(s.log) > limit {
		start = len(s.log) - limit
	}
	entries := make([]any, 0, len(s.log)-start)
	for _, item := range s.log[start:] {
		entries = append(entries, Value{
			"owner":        item.Owner,
			"state_digest": digestOf(item.State),
			"status":       stringValue(object(object(item.State["autoscaling_group"])["instance_refresh"])["status"]),
		})
	}
	writeJSON(w, http.StatusOK, Value{"count": len(s.log), "entries": entries})
}

func (s *store) digest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	writeJSON(w, http.StatusOK, Value{
		"state_digest": stringValue(s.state["state_digest"]),
		"computed":     digestOf(s.state),
		"owner":        s.ownerInProgress(),
		"instances":    len(anyList(s.state["instances"])),
		"volumes":      len(anyList(s.state["ebs_volumes"])),
	})
}

func anyList(value any) []any {
	list, _ := value.([]any)
	return list
}
