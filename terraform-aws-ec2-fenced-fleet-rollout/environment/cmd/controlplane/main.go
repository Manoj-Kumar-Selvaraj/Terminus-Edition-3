package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sync"
)

type Value map[string]any

type store struct {
	mu    sync.Mutex
	path  string
	state Value
}

func load(path string) (Value, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Value{}, nil
		}
		return nil, err
	}
	result := Value{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func atomicWrite(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	tmp, err := os.CreateTemp(filepath.Dir(path), filepath.Base(path)+".")
	if err != nil {
		return err
	}
	name := tmp.Name()
	defer os.Remove(name)
	if _, err := tmp.Write(data); err == nil {
		err = tmp.Sync()
	}
	if closeErr := tmp.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return err
	}
	return os.Rename(name, path)
}

func (s *store) inventory(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(s.state)
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
	currentRefresh := object(object(s.state["autoscaling_group"])["instance_refresh"])
	if stringValue(currentRefresh["status"]) == "in_progress" {
		if stringValue(currentRefresh["owner_token"]) != "" && stringValue(currentRefresh["owner_token"]) != owner {
			http.Error(w, "stale rollout owner", http.StatusConflict)
			return
		}
	}
	s.state = Value(state)
	if err := atomicWrite(s.path, s.state); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	lost, _ := payload["control_plane_response_lost"].(bool)
	if lost {
		w.WriteHeader(http.StatusServiceUnavailable)
		_ = json.NewEncoder(w).Encode(Value{"committed": true, "error": "control plane response lost"})
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(Value{"committed": true, "inventory": s.state})
}

func (s *store) reset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state = Value{}
	_ = os.Remove(s.path)
	w.WriteHeader(http.StatusNoContent)
}

func object(value any) Value {
	if result, ok := value.(Value); ok {
		return result
	}
	if result, ok := value.(map[string]any); ok {
		return result
	}
	return Value{}
}

func stringValue(value any) string {
	if value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return fmt.Sprint(value)
}

func main() {
	listen := flag.String("listen", "127.0.0.1:18080", "listen address")
	statePath := flag.String("state", "/app/var/fleet/controlplane-state.json", "durable inventory path")
	flag.Parse()
	current, err := load(*statePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	s := &store{path: *statePath, state: current}
	mux := http.NewServeMux()
	mux.HandleFunc("/v1/inventory", s.inventory)
	mux.HandleFunc("/v1/commit", s.commit)
	mux.HandleFunc("/v1/reset", s.reset)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	fmt.Fprintf(os.Stderr, "ec2-controlplane listening on %s\n", *listen)
	if err := http.ListenAndServe(*listen, mux); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
