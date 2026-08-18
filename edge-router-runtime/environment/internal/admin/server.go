package admin

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"edge-router/internal/checkpoint"
	"edge-router/internal/config"
	"edge-router/internal/drain"
	"edge-router/internal/health"
	"edge-router/internal/reconcile"
	rt "edge-router/internal/runtime"
	"edge-router/internal/telemetry"
)

type Server struct {
	server *http.Server
	ingress *config.Ingress
	reconciler *reconcile.Reconciler
	store *rt.PublicationStore
	registry *rt.Registry
	health *health.Manager
	drain *drain.Manager
	checkpoints *checkpoint.Store
	metrics *telemetry.Registry
	logger *slog.Logger
}

func New(addr string, ingress *config.Ingress, reconciler *reconcile.Reconciler, store *rt.PublicationStore, registry *rt.Registry, healthManager *health.Manager, drainManager *drain.Manager, checkpoints *checkpoint.Store, metrics *telemetry.Registry, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.Default()
	}
	s := &Server{
		ingress: ingress,
		reconciler: reconciler,
		store: store,
		registry: registry,
		health: healthManager,
		drain: drainManager,
		checkpoints: checkpoints,
		metrics: metrics,
		logger: logger,
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", s.healthz)
	mux.HandleFunc("GET /readyz", s.readyz)
	mux.HandleFunc("GET /v1/status", s.status)
	mux.HandleFunc("GET /v1/runtime", s.runtimeState)
	mux.HandleFunc("GET /v1/health", s.healthState)
	mux.HandleFunc("GET /v1/drains", s.drains)
	mux.HandleFunc("GET /v1/checkpoints", s.checkpointList)
	mux.HandleFunc("POST /v1/config/snapshot", s.submit)
	mux.HandleFunc("POST /v1/discovery/snapshot", s.submit)
	mux.HandleFunc("GET /metrics", s.metricsEndpoint)
	s.server = &http.Server{
		Addr: addr,
		Handler: requestLogging(logger, mux),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout: 60 * time.Second,
	}
	return s
}

func (s *Server) ListenAndServe() error {
	err := s.server.ListenAndServe()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func (s *Server) Shutdown(ctx context.Context) error {
	return s.server.Shutdown(ctx)
}

func (s *Server) healthz(writer http.ResponseWriter, _ *http.Request) {
	writeJSON(writer, http.StatusOK, map[string]any{"status": "ok", "time": time.Now().UTC()})
}

func (s *Server) readyz(writer http.ResponseWriter, _ *http.Request) {
	status := s.reconciler.Status()
	if !status.Ready || s.store.Current() == nil {
		writeJSON(writer, http.StatusServiceUnavailable, map[string]any{"ready": false, "generation": status.Generation})
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"ready": true, "generation": status.Generation})
}

func (s *Server) status(writer http.ResponseWriter, _ *http.Request) {
	status := s.reconciler.Status()
	current := s.store.Current()
	response := map[string]any{
		"reconcile": status,
		"pools_runtime": s.registry.PoolCount(),
		"endpoints_runtime": s.registry.EndpointCount(),
		"metrics_cardinality": s.metrics.Cardinality(),
	}
	if current != nil {
		response["serving_generation"] = current.Generation
		response["route_count"] = len(current.Routes)
		response["pool_count"] = len(current.Pools)
		response["leases"] = current.LeaseCount()
	}
	writeJSON(writer, http.StatusOK, response)
}

func (s *Server) runtimeState(writer http.ResponseWriter, _ *http.Request) {
	current := s.store.Current()
	if current == nil {
		writeJSON(writer, http.StatusServiceUnavailable, map[string]any{"error": "no published generation"})
		return
	}
	type endpoint struct {
		Pool string `json:"pool"`
		Identity string `json:"identity"`
		Address string `json:"address"`
		Incarnation uint64 `json:"incarnation"`
		Membership rt.MembershipState `json:"membership"`
		Health rt.HealthState `json:"health"`
		Inflight int64 `json:"inflight"`
		Connections int64 `json:"connections"`
	}
	items := make([]endpoint, 0)
	for poolID, pool := range current.Pools {
		for _, view := range pool.Endpoints {
			if view.Runtime == nil {
				continue
			}
			inflight, connections := view.Runtime.Counts()
			items = append(items, endpoint{
				Pool: poolID,
				Identity: view.Identity,
				Address: view.Address,
				Incarnation: view.Incarnation,
				Membership: view.Runtime.Membership(),
				Health: view.Runtime.Health(),
				Inflight: inflight,
				Connections: connections,
			})
		}
	}
	writeJSON(writer, http.StatusOK, map[string]any{"generation": current.Generation, "endpoints": items})
}

func (s *Server) healthState(writer http.ResponseWriter, request *http.Request) {
	limit := parseLimit(request.URL.Query().Get("limit"), 64, 256)
	writeJSON(writer, http.StatusOK, map[string]any{"observations": s.health.History(limit)})
}

func (s *Server) drains(writer http.ResponseWriter, request *http.Request) {
	limit := parseLimit(request.URL.Query().Get("limit"), 64, 256)
	writeJSON(writer, http.StatusOK, map[string]any{
		"draining": s.drain.Draining(),
		"recently_retired": s.drain.Retired(limit),
	})
}

func (s *Server) checkpointList(writer http.ResponseWriter, _ *http.Request) {
	items, err := s.checkpoints.List()
	if err != nil {
		writeJSON(writer, http.StatusInternalServerError, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"checkpoints": items})
}

func (s *Server) submit(writer http.ResponseWriter, request *http.Request) {
	body := io.LimitReader(request.Body, 8<<20)
	snapshot, err := config.ParseSource(body)
	if err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]any{"error": err.Error()})
		return
	}
	resultChannel, err := s.ingress.Submit(request.Context(), snapshot)
	if err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]any{"error": err.Error()})
		return
	}
	select {
	case result := <-resultChannel:
		status := http.StatusAccepted
		if result.Status == config.StatusRejected || result.Status == config.StatusConflict {
			status = http.StatusConflict
		}
		if result.Status == config.StatusStale {
			status = http.StatusPreconditionFailed
		}
		writeJSON(writer, status, result)
	case <-request.Context().Done():
		writeJSON(writer, http.StatusRequestTimeout, map[string]any{"error": request.Context().Err().Error()})
	case <-time.After(10 * time.Second):
		writeJSON(writer, http.StatusGatewayTimeout, map[string]any{"error": "reconciliation did not complete before admin timeout"})
	}
}

func (s *Server) metricsEndpoint(writer http.ResponseWriter, _ *http.Request) {
	writer.Header().Set("Content-Type", "text/plain; version=0.0.4")
	_, _ = writer.Write(s.metrics.Prometheus())
}

func writeJSON(writer http.ResponseWriter, status int, value any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(value)
}

func parseLimit(raw string, fallback, maximum int) int {
	if strings.TrimSpace(raw) == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil || value < 1 {
		return fallback
	}
	if value > maximum {
		return maximum
	}
	return value
}

func requestLogging(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		started := time.Now()
		next.ServeHTTP(writer, request)
		logger.Debug("admin request", "method", request.Method, "path", request.URL.Path, "duration", time.Since(started))
	})
}
