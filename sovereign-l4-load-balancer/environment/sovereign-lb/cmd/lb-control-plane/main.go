package main

import (
	"context"
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"sovereign-lb/internal/api"
)

func main() {
	management := flag.String("management", "127.0.0.1:16080", "management HTTP address")
	control := flag.String("control", "127.0.0.1:16081", "dataplane control address")
	state := flag.String("state", "/app/sovereign-lb/state/control", "durable state directory")
	flag.Parse()
	service, err := api.Open(*state); if err != nil { log.Fatal(err) }
	listener, err := net.Listen("tcp", *control); if err != nil { log.Fatal(err) }
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM); defer stop()
	go func() { if serveErr := service.ServeControl(ctx, listener, 4<<20); serveErr != nil { log.Printf("control server: %v", serveErr); stop() } }()
	server := &http.Server{Addr:*management,Handler:service.Router(),ReadHeaderTimeout:5*time.Second,IdleTimeout:60*time.Second}
	go func() { <-ctx.Done(); shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second); defer cancel(); _ = server.Shutdown(shutdown) }()
	log.Printf("management=%s control=%s state=%s", *management, *control, *state)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed { log.Fatal(err) }
}