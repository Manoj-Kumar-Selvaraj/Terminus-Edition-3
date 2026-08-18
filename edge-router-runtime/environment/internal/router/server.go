package router

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"sync/atomic"
	"time"

	rt "edge-router/internal/runtime"
	"edge-router/internal/selection"
	"edge-router/internal/telemetry"
	"edge-router/internal/upstream"
)

type Server struct {
	store *rt.PublicationStore
	selector *selection.Engine
	transport *upstream.Transport
	metrics *telemetry.Registry
	logger *slog.Logger
	server *http.Server
	ready atomic.Bool
	maxRequestBody int64
}

func New(addr string, store *rt.PublicationStore, selector *selection.Engine, transport *upstream.Transport, metrics *telemetry.Registry, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.Default()
	}
	s := &Server{
		store: store,
		selector: selector,
		transport: transport,
		metrics: metrics,
		logger: logger,
		maxRequestBody: 4 << 20,
	}
	s.server = &http.Server{
		Addr: addr,
		Handler: http.HandlerFunc(s.handle),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout: 90 * time.Second,
	}
	return s
}

func (s *Server) SetReady(ready bool) {
	s.ready.Store(ready)
}

func (s *Server) ListenAndServe() error {
	s.ready.Store(true)
	err := s.server.ListenAndServe()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func (s *Server) Shutdown(ctx context.Context) error {
	s.ready.Store(false)
	return s.server.Shutdown(ctx)
}

func (s *Server) handle(writer http.ResponseWriter, request *http.Request) {
	started := time.Now()
	if !s.ready.Load() {
		http.Error(writer, "edge router not ready", http.StatusServiceUnavailable)
		return
	}
	lease := s.store.Acquire()
	if lease == nil || lease.Snapshot == nil {
		http.Error(writer, "no published route generation", http.StatusServiceUnavailable)
		return
	}
	defer lease.Release()
	route, ok := matchRoute(lease.Snapshot, request)
	if !ok {
		http.Error(writer, "route not found", http.StatusNotFound)
		s.metrics.Add(telemetry.GenerationOwner(lease.Snapshot.Generation), "edge_router_requests_total", map[string]string{"result": "not_found"}, 1)
		return
	}
	body, err := readBody(request.Body, s.maxRequestBody)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusRequestEntityTooLarge)
		return
	}
	request.Body = io.NopCloser(bytes.NewReader(body))
	state := &selection.RequestState{}
	result, choice, err := s.proxyWithRetries(request.Context(), request, body, route, state)
	if err != nil {
		s.logger.Warn("upstream request failed", "route", route.ID, "pool", route.PoolID, "error", err)
		http.Error(writer, "upstream unavailable", http.StatusServiceUnavailable)
		s.metrics.Add(telemetry.GenerationOwner(lease.Snapshot.Generation), "edge_router_requests_total", map[string]string{"route": route.ID, "result": "unavailable"}, 1)
		return
	}
	copyResponseHeaders(writer.Header(), result.Header)
	writer.Header().Set("X-Edge-Generation", fmt.Sprintf("%d", lease.Snapshot.Generation))
	writer.Header().Set("X-Edge-Pool", choice.PoolID)
	writer.WriteHeader(result.StatusCode)
	_, _ = writer.Write(result.Body)
	owner := telemetry.GenerationOwner(lease.Snapshot.Generation)
	s.metrics.Add(owner, "edge_router_requests_total", map[string]string{"route": route.ID, "pool": choice.PoolID, "status": fmt.Sprintf("%d", result.StatusCode)}, 1)
	s.metrics.Set(owner, "edge_router_request_duration_milliseconds", map[string]string{"route": route.ID}, float64(time.Since(started).Milliseconds()))
}

func (s *Server) proxyWithRetries(ctx context.Context, request *http.Request, body []byte, route rt.CompiledRoute, state *selection.RequestState) (upstream.Result, selection.Choice, error) {
	current := s.store.Current()
	if current == nil {
		return upstream.Result{}, selection.Choice{}, errors.New("no current generation")
	}
	pool := current.Pools[route.PoolID]
	if pool == nil {
		return upstream.Result{}, selection.Choice{}, fmt.Errorf("pool %s missing", route.PoolID)
	}
	attempts := selection.Attempts(pool.Retry)
	var lastErr error
	var lastResult upstream.Result
	var lastChoice selection.Choice
	for attempt := 0; attempt < attempts; attempt++ {
		lease := s.store.Acquire()
		if lease == nil || lease.Snapshot == nil {
			return lastResult, lastChoice, errors.New("generation disappeared")
		}
		choice, err := s.selector.Select(lease.Snapshot, route.PoolID, request, state)
		lease.Release()
		if err != nil {
			lastErr = err
			break
		}
		lastChoice = choice
		result, err := s.transport.Do(ctx, choice.Runtime, request, body)
		lastResult = result
		s.selector.MarkAttempt(state, choice)
		if err != nil {
			lastErr = err
			continue
		}
		if !selection.Retryable(result.StatusCode, pool.Retry) {
			return result, choice, nil
		}
		lastErr = fmt.Errorf("retryable upstream status %d", result.StatusCode)
	}
	if lastErr == nil {
		lastErr = errors.New("retry budget exhausted")
	}
	return lastResult, lastChoice, lastErr
}

func matchRoute(snapshot *rt.RuntimeSnapshot, request *http.Request) (rt.CompiledRoute, bool) {
	if snapshot == nil {
		return rt.CompiledRoute{}, false
	}
	host := request.Host
	if index := strings.IndexByte(host, ':'); index >= 0 {
		host = host[:index]
	}
	host = strings.ToLower(host)
	for _, route := range snapshot.Routes {
		if route.Host != "" && route.Host != host {
			continue
		}
		if route.PathPrefix != "" && !strings.HasPrefix(request.URL.Path, route.PathPrefix) {
			continue
		}
		if len(route.Methods) > 0 {
			if _, exists := route.Methods[request.Method]; !exists {
				continue
			}
		}
		return route, true
	}
	return rt.CompiledRoute{}, false
}

func readBody(reader io.ReadCloser, limit int64) ([]byte, error) {
	if reader == nil {
		return nil, nil
	}
	defer reader.Close()
	body, err := io.ReadAll(io.LimitReader(reader, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(body)) > limit {
		return nil, errors.New("request body exceeds configured limit")
	}
	return body, nil
}

func copyResponseHeaders(destination, source http.Header) {
	for key, values := range source {
		if hopByHop(key) {
			continue
		}
		for _, value := range values {
			destination.Add(key, value)
		}
	}
}

func hopByHop(key string) bool {
	switch strings.ToLower(key) {
	case "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade":
		return true
	default:
		return false
	}
}

func (s *Server) Debug(writer http.ResponseWriter, request *http.Request) {
	lease := s.store.Acquire()
	if lease == nil {
		http.Error(writer, "no generation", http.StatusServiceUnavailable)
		return
	}
	defer lease.Release()
	payload := map[string]any{
		"generation": lease.Snapshot.Generation,
		"routes": len(lease.Snapshot.Routes),
		"pools": len(lease.Snapshot.Pools),
		"leases": lease.Snapshot.LeaseCount(),
	}
	writer.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(writer).Encode(payload)
}
