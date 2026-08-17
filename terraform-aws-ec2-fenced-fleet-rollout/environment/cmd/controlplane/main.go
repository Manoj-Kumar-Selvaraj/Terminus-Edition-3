package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"
)

func osRemove(path string) error {
	return os.Remove(path)
}

func main() {
	listen := flag.String("listen", "127.0.0.1:18080", "listen address")
	statePath := flag.String("state", "/app/var/fleet/controlplane-state.json", "durable inventory path")
	flag.Parse()
	current, err := loadValue(*statePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	logPath := *statePath + ".commits.json"
	log := []snapshot{}
	if raw, err := loadValue(logPath); err == nil && raw != nil {
		if items, ok := raw["entries"].([]any); ok {
			for _, item := range items {
				entry := object(item)
				log = append(log, snapshot{Owner: stringValue(entry["owner"]), State: object(entry["state"])})
			}
		}
	}
	s := &store{path: *statePath, logPath: logPath, state: current, log: log}
	mux := http.NewServeMux()
	mux.HandleFunc("/v1/inventory", s.inventory)
	mux.HandleFunc("/v1/commit", s.commit)
	mux.HandleFunc("/v1/reset", s.reset)
	mux.HandleFunc("/v1/commits", s.commits)
	mux.HandleFunc("/v1/digest", s.digest)
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
