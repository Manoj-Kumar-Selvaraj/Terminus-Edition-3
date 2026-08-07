package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"edgectl/internal/api"
	"edgectl/internal/config"
	"edgectl/internal/store"
	"edgectl/internal/traffic"
)

func main() {
	listen := flag.String("listen", "127.0.0.1:8787", "HTTP listen address")
	stateDir := flag.String("state", "/app/var/edge/state", "directory for persisted JSON state")
	configPath := flag.String("config", "/app/var/edge/edgectl.json", "path to edgectl configuration JSON")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "edgectl: configuration rejected: %v\n", err)
		os.Exit(2)
	}

	st, err := store.Open(*stateDir, cfg.WindowSize)
	if err != nil {
		fmt.Fprintf(os.Stderr, "edgectl: state directory unusable: %v\n", err)
		os.Exit(3)
	}

	sim := traffic.New(st, cfg)
	sim.Start()
	defer sim.Stop()

	srv := &http.Server{
		Addr:    *listen,
		Handler: api.New(cfg, st, sim),
	}

	errCh := make(chan error, 1)
	go func() {
		log.Printf("edgectl listening on %s (state=%s config=%s digest=%s)", *listen, *stateDir, *configPath, cfg.Digest)
		errCh <- srv.ListenAndServe()
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		log.Printf("edgectl shutting down on %s", sig)
		_ = srv.Close()
		sim.Stop()
		_ = st.PersistNow()
	case err := <-errCh:
		if err != nil && err != http.ErrServerClosed {
			fmt.Fprintf(os.Stderr, "edgectl: %v\n", err)
			os.Exit(1)
		}
	}
}
