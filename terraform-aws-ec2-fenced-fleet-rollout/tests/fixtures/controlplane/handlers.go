package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
)

func digestOf(value any) string {
	data, _ := json.Marshal(value)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func (s *store) inventory(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	payload := object(s.state)
	if len(payload) == 0 {
		writeJSON(w, http.StatusOK, Value{"instances": []any{}, "ebs_volumes": []any{}, "state_digest": ""})
		return
	}
	if stringValue(payload["state_digest"]) == "" {
		payload["state_digest"] = digestOf(payload)
	}
	writeJSON(w, http.StatusOK, payload)
}

func (s *store) commit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	payload := Value{}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	state, _ := payload["state"].(map[string]any)
	if state == nil {
		http.Error(w, "state is required", http.StatusBadRequest)
		return
	}
	owner, _ := payload["owner_token"].(string)
	s.mu.Lock()
	defer s.mu.Unlock()
	currentOwner := s.ownerInProgress()
	if currentOwner != "" && currentOwner != owner {
		http.Error(w, "stale rollout owner", http.StatusConflict)
		return
	}
	s.state = Value(state)
	if stringValue(s.state["state_digest"]) == "" {
		s.state["state_digest"] = digestOf(s.state)
	}
	s.log = append(s.log, snapshot{Owner: owner, State: object(s.state)})
	if err := s.persist(); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	lost, _ := payload["control_plane_response_lost"].(bool)
	if lost {
		writeJSON(w, http.StatusServiceUnavailable, Value{"committed": true, "error": "control plane response lost"})
		return
	}
	writeJSON(w, http.StatusOK, Value{"committed": true, "inventory": s.state})
}

func (s *store) reset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state = Value{}
	s.log = nil
	_ = osRemove(s.path)
	_ = osRemove(s.logPath)
	w.WriteHeader(http.StatusNoContent)
}
