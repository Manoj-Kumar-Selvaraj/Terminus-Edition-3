package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
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

var baseHopHeaders = []string{
	"Connection", "Proxy-Connection", "Keep-Alive", "Proxy-Authenticate",
	"Proxy-Authorization", "Te", "Trailer", "Transfer-Encoding", "Upgrade",
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
	if c.Listen == "" || c.AdminListen == "" {
		return nil, errors.New("listeners are required")
	}
	if c.ShutdownTimeoutMS <= 0 || c.UpstreamTimeoutMS <= 0 {
		return nil, errors.New("timeouts must be positive")
	}
	if len(c.Routes) == 0 {
		return nil, errors.New("at least one route is required")
	}
	for i := range c.Routes {
		r := &c.Routes[i]
		if r.Host == "" || !strings.HasPrefix(r.PathPrefix, "/") || len(r.Upstreams) == 0 {
			return nil, fmt.Errorf("invalid route %d", i)
		}
		for _, raw := range r.Upstreams {
			u, err := url.Parse(raw)
			if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
				return nil, fmt.Errorf("invalid upstream %q", raw)
			}
		}
	}
	return &c, nil
}

func requestHost(hostport string) string {
	h := hostport
	if host, _, err := net.SplitHostPort(hostport); err == nil {
		h = host
	} else if strings.HasPrefix(hostport, "[") && strings.Contains(hostport, "]") {
		h = strings.Trim(hostport, "[]")
	} else if i := strings.LastIndex(hostport, ":"); i > -1 && strings.Count(hostport, ":") == 1 {
		h = hostport[:i]
	}
	return strings.ToLower(strings.TrimSuffix(h, "."))
}

func hostMatches(rule, host string) (bool, int) {
	rule = strings.ToLower(strings.TrimSuffix(rule, "."))
	host = requestHost(host)
	if strings.HasPrefix(rule, "*.") {
		suffix := strings.TrimPrefix(rule, "*.")
		if host == suffix {
			return false, 0
		}
		return strings.HasSuffix(host, "."+suffix), 1
	}
	return rule == host, 2
}

func chooseRoute(s *Snapshot, r *http.Request) *Route {
	best := -1
	bestHostClass := -1
	bestPrefixLen := -1
	for i := range s.Config.Routes {
		route := &s.Config.Routes[i]
		matched, hostClass := hostMatches(route.Host, r.Host)
		if !matched || !strings.HasPrefix(r.URL.Path, route.PathPrefix) {
			continue
		}
		pl := len(route.PathPrefix)
		if hostClass > bestHostClass || (hostClass == bestHostClass && pl > bestPrefixLen) {
			best = i
			bestHostClass = hostClass
			bestPrefixLen = pl
		}
	}
	if best < 0 {
		return nil
	}
	return &s.Config.Routes[best]
}

func connectionTokens(h http.Header) []string {
	var out []string
	for _, v := range h.Values("Connection") {
		for _, token := range strings.Split(v, ",") {
			token = strings.TrimSpace(token)
			if token != "" {
				out = append(out, token)
			}
		}
	}
	return out
}

func stripHop(h http.Header) {
	for _, token := range connectionTokens(h) {
		h.Del(token)
	}
	for _, k := range baseHopHeaders {
		h.Del(k)
	}
}

func cloneHeader(src http.Header) http.Header {
	dst := make(http.Header, len(src))
	for k, vv := range src {
		dst[k] = append([]string(nil), vv...)
	}
	return dst
}

func clientIP(remote string) string {
	if host, _, err := net.SplitHostPort(remote); err == nil {
		return host
	}
	return remote
}

func appendForwardedFor(h http.Header, ip string) {
	prior := strings.TrimSpace(h.Get("X-Forwarded-For"))
	if prior == "" {
		h.Set("X-Forwarded-For", ip)
		return
	}
	h.Set("X-Forwarded-For", prior+", "+ip)
}

func replayable(r *http.Request) bool {
	if r.Method != http.MethodGet && r.Method != http.MethodHead && r.Method != http.MethodOptions {
		return false
	}
	return r.Body == nil || r.Body == http.NoBody || r.ContentLength == 0
}

func copyResponse(w http.ResponseWriter, resp *http.Response) error {
	stripHop(resp.Header)
	for k, vv := range resp.Header {
		for _, v := range vv {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	_, err := io.Copy(w, resp.Body)
	return err
}

func (rt *Runtime) proxyHandler(w http.ResponseWriter, r *http.Request) {
	s := rt.current.Load()
	if s == nil {
		http.Error(w, "not ready", http.StatusServiceUnavailable)
		return
	}
	route := chooseRoute(s, r)
	if route == nil {
		http.NotFound(w, r)
		return
	}

	start := route.rr.Add(1) - 1
	maxAttempts := 1
	if replayable(r) && len(route.Upstreams) > 1 {
		maxAttempts = 2
	}

	for attempt := 0; attempt < maxAttempts; attempt++ {
		target, _ := url.Parse(route.Upstreams[(int(start)+attempt)%len(route.Upstreams)])
		outURL := *r.URL
		outURL.Scheme = target.Scheme
		outURL.Host = target.Host
		if target.Path != "" && target.Path != "/" {
			outURL.Path = strings.TrimSuffix(target.Path, "/") + "/" + strings.TrimPrefix(r.URL.Path, "/")
		}

		ctx, cancel := context.WithTimeout(r.Context(), time.Duration(s.Config.UpstreamTimeoutMS)*time.Millisecond)
		var body io.ReadCloser = r.Body
		if attempt > 0 {
			body = http.NoBody
		}
		upReq, err := http.NewRequestWithContext(ctx, r.Method, outURL.String(), body)
		if err != nil {
			cancel()
			http.Error(w, "bad gateway", http.StatusBadGateway)
			return
		}
		upReq.Header = cloneHeader(r.Header)
		stripHop(upReq.Header)
		upReq.Host = r.Host
		appendForwardedFor(upReq.Header, clientIP(r.RemoteAddr))
		upReq.Header.Set("X-Forwarded-Host", r.Host)
		upReq.Header.Set("X-Forwarded-Proto", "http")

		resp, err := http.DefaultTransport.RoundTrip(upReq)
		if err != nil {
			cancel()
			if attempt+1 < maxAttempts {
				continue
			}
			http.Error(w, "bad gateway", http.StatusBadGateway)
			return
		}
		err = copyResponse(w, resp)
		_ = resp.Body.Close()
		cancel()
		if err != nil {
			return
		}
		return
	}
}

func (rt *Runtime) adminHandler(w http.ResponseWriter, r *http.Request) {
	s := rt.current.Load()
	if s == nil {
		http.Error(w, "not ready", http.StatusServiceUnavailable)
		return
	}
	if r.Method != http.MethodGet {
		http.NotFound(w, r)
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
	if old == nil {
		return
	}
	cfg, err := loadConfig(rt.path)
	if err != nil {
		log.Printf("reload rejected: %v", err)
		return
	}
	if cfg.Listen != old.Config.Listen || cfg.AdminListen != old.Config.AdminListen {
		log.Printf("reload rejected: listener addresses are immutable")
		return
	}
	rt.current.Store(&Snapshot{Config: cfg, Generation: old.Generation + 1})
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
	select {
	case sig := <-sigCh:
		for sig == syscall.SIGHUP {
			rt.reload()
			sig = <-sigCh
		}
	case err := <-errCh:
		if err != nil && err != http.ErrServerClosed {
			log.Printf("listener failed: %v", err)
		}
	}

	timeout := time.Duration(cfg.ShutdownTimeoutMS) * time.Millisecond
	if s := rt.current.Load(); s != nil {
		timeout = time.Duration(s.Config.ShutdownTimeoutMS) * time.Millisecond
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	var wg sync.WaitGroup
	wg.Add(2)
	go func() { defer wg.Done(); _ = public.Shutdown(ctx) }()
	go func() { defer wg.Done(); _ = admin.Shutdown(ctx) }()
	wg.Wait()
}
