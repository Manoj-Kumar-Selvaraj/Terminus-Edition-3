package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"outbox/internal/api"
	"outbox/internal/clock"
	"outbox/internal/config"
	"outbox/internal/service"
	"outbox/internal/store"
	"outbox/internal/reconcile"
	"outbox/internal/worker"
)

func main() {
	cfg := config.Load()
	if err := os.MkdirAll(cfg.Data, 0o755); err != nil {
		fatal(err)
	}
	st, err := store.Open(cfg.DBPath, cfg.SchemaPath(), clock.System{})
	if err != nil {
		fatal(err)
	}
	defer st.Close()

	svc := service.New(st, cfg.Token, cfg.Sync)
	srv := api.NewServer(cfg, svc, st)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if !cfg.Sync {
		loop := &worker.Loop{Store: st, Svc: svc, Owner: "outboxd", Every: time.Second, Batch: 20}
		go loop.Start(ctx)
		go func() {
			sw := &reconcile.Sweeper{Store: st}
			t := time.NewTicker(5 * time.Second)
			defer t.Stop()
			for {
				select {
				case <-ctx.Done():
					return
				case <-t.C:
					_, _ = sw.ExpireStaleLeases(st.Now())
				}
			}
		}()
	}

	httpSrv := &http.Server{Addr: cfg.Addr, Handler: srv.Handler()}
	go func() {
		fmt.Fprintf(os.Stderr, "outboxd listening on %s db=%s\n", cfg.Addr, cfg.DBPath)
		if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fatal(err)
		}
	}()

	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
	<-ch
	cancel()
	shutdownCtx, c2 := context.WithTimeout(context.Background(), 5*time.Second)
	defer c2()
	_ = httpSrv.Shutdown(shutdownCtx)
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
