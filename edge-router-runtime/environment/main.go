package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

type Config struct {
	Listen            string  `json:"listen"`
	AdminListen       string  `json:"admin_listen"`
	ShutdownTimeoutMS int     `json:"shutdown_timeout_ms"`
	UpstreamTimeoutMS int     `json:"upstream_timeout_ms"`
	Routes            []Route `json:"routes"`
}

type Route struct {
	Host       string   `json:"host"`
	PathPrefix string   `json:"path_prefix"`
	Upstreams  []string `json:"upstreams"`
	rr         atomic.Uint64
}

type Snapshot struct {
	Config     *Config
	Generation uint64
}

type Runtime struct {
	path     string
	current  atomic.Pointer[Snapshot]
	reloadMu sync.Mutex
}

func loadConfig(path string) (*Config, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Config
	if err := json.Unmarshal(b, &c); err != nil {
		return nil, err
	}
	if c.Listen == "" || c.AdminListen == "" || len(c.Routes) == 0 {
		return nil, fmt.Errorf("incomplete config")
	}
	for _, r := range c.Routes {
		if r.Host == "" || r.PathPrefix == "" || len(r.Upstreams) == 0 {
			return nil, fmt.Errorf("invalid route")
		}
		for _, raw := range r.Upstreams {
			if _, err := url.Parse(raw); err != nil {
				return nil, err
			}
		}
	}
	return &c, nil
}

func hostMatches(rule, host string) bool {
	host = strings.ToLower(strings.Split(host, ":")[0])
	rule = strings.ToLower(rule)
	if strings.HasPrefix(rule, "*.") {
		return strings.HasSuffix(host, strings.TrimPrefix(rule, "*"))
	}
	return rule == host
}

func (rt *Runtime) chooseRoute(r *http.Request) *Route {
	s := rt.current.Load()
	if s == nil {
		return nil
	}
	for i := range s.Config.Routes {
		route := &s.Config.Routes[i]
		if hostMatches(route.Host, r.Host) && strings.HasPrefix(r.URL.Path, route.PathPrefix) {
			return route
		}
	}
	return nil
}

func hopHeaders() map[string]struct{} {
	return map[string]struct{}{
		"Connection": {}, "Proxy-Connection": {}, "Keep-Alive": {}, "Proxy-Authenticate": {},
		"Proxy-Authorization": {}, "Te": {}, "Trailer": {}, "Transfer-Encoding": {}, "Upgrade": {},
	}
}

func stripHop(h http.Header) {
	for k := range hopHeaders() {
		h.Del(k)
	}
}

func (rt *Runtime) proxyHandler(w http.ResponseWriter, r *http.Request) {
	route := rt.chooseRoute(r)
	if route == nil {
		http.NotFound(w, r)
		return
	}

	start := route.rr.Add(1) - 1
	attempts := len(route.Upstreams)
	if attempts > 2 {
		attempts = 2
	}
	var lastErr error
	for i := 0; i < attempts; i++ {
		raw := route.Upstreams[(int(start)+i)%len(route.Upstreams)]
		target, err := url.Parse(raw)
		if err != nil {
			lastErr = err
			continue
		}

		proxy := httputil.NewSingleHostReverseProxy(target)
		orig := proxy.Director
		proxy.Director = func(req *http.Request) {
			orig(req)
			req.Host = r.Host
			stripHop(req.Header)
			req.Header.Set("X-Forwarded-For", r.RemoteAddr)
			req.Header.Set("X-Forwarded-Host", r.Host)
			req.Header.Set("X-Forwarded-Proto", "http")
		}
		proxy.ErrorHandler = func(rw http.ResponseWriter, req *http.Request, e error) {
			lastErr = e
		}
		proxy.ModifyResponse = func(resp *http.Response) error {
			stripHop(resp.Header)
			return nil
		}
		proxy.ServeHTTP(w, r)
		if lastErr == nil {
			return
		}
	}
	if lastErr != nil {
		http.Error(w, "bad gateway", http.StatusBadGateway)
	}
}

func (rt *Runtime) adminHandler(w http.ResponseWriter, r *http.Request) {
	s := rt.current.Load()
	if s == nil {
		http.Error(w, "not ready", http.StatusServiceUnavailable)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	switch r.URL.Path {
	case "/_edge/health":
		_ = json.NewEncoder(w).Encode(map[string]any{"status": "ok", "generation": s.Generation})
	case "/_edge/config":
		_ = json.NewEncoder(w).Encode(map[string]any{"generation": s.Generation, "route_count": len(s.Config.Routes)})
	default:
		http.NotFound(w, r)
	}
}

func (rt *Runtime) reload() {
	rt.reloadMu.Lock()
	defer rt.reloadMu.Unlock()
	old := rt.current.Load()
	rt.current.Store(nil)
	cfg, err := loadConfig(rt.path)
	if err != nil {
		log.Printf("reload rejected: %v", err)
		return
	}
	gen := uint64(1)
	if old != nil {
		gen = old.Generation + 1
	}
	rt.current.Store(&Snapshot{Config: cfg, Generation: gen})
}

func main() {
	configPath := flag.String("config", "/app/edge-router/config.json", "config path")
	flag.Parse()
	cfg, err := loadConfig(*configPath)
	if err != nil {
		log.Fatal(err)
	}
	rt := &Runtime{path: *configPath}
	rt.current.Store(&Snapshot{Config: cfg, Generation: 1})

	public := &http.Server{Addr: cfg.Listen, Handler: http.HandlerFunc(rt.proxyHandler), ReadHeaderTimeout: 5 * time.Second}
	admin := &http.Server{Addr: cfg.AdminListen, Handler: http.HandlerFunc(rt.adminHandler), ReadHeaderTimeout: 5 * time.Second}

	errCh := make(chan error, 2)
	go func() { errCh <- public.ListenAndServe() }()
	go func() { errCh <- admin.ListenAndServe() }()

	sigCh := make(chan os.Signal, 2)
	signal.Notify(sigCh, syscall.SIGHUP, syscall.SIGTERM, syscall.SIGINT)
	for {
		select {
		case sig := <-sigCh:
			if sig == syscall.SIGHUP {
				rt.reload()
				continue
			}
			_ = public.Close()
			_ = admin.Close()
			os.Exit(0)
		case err := <-errCh:
			if err != nil && err != http.ErrServerClosed {
				log.Fatal(err)
			}
			ctx, cancel := context.WithTimeout(context.Background(), time.Second)
			_ = public.Shutdown(ctx)
			_ = admin.Shutdown(ctx)
			cancel()
			return
		}
	}
}
