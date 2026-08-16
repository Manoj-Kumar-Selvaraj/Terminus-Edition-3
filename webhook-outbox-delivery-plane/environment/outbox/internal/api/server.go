package api

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"outbox/internal/config"
	"outbox/internal/policy"
	"outbox/internal/service"
	"outbox/internal/store"
)

type Server struct {
	Cfg  config.Config
	Svc  *service.Outbox
	Store *store.Store
	Mux  *http.ServeMux
}

func NewServer(cfg config.Config, svc *service.Outbox, st *store.Store) *Server {
	s := &Server{Cfg: cfg, Svc: svc, Store: st, Mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) Handler() http.Handler {
	return CORSDev(Logging(MaxBody(s.Mux, 1<<20)))
}

func (s *Server) routes() {
	s.Mux.HandleFunc("/api/v1/health", s.handleHealth)
	s.Mux.HandleFunc("/api/v1/stats", s.handleStats)
	s.Mux.HandleFunc("/api/v1/tenants", s.handleTenants)
	s.Mux.HandleFunc("/api/v1/tenants/", s.handleTenantsSub)
	s.Mux.HandleFunc("/api/v1/endpoints/", s.handleEndpointsSub)
	s.Mux.HandleFunc("/api/v1/events/", s.handleEventsSub)
	s.Mux.HandleFunc("/api/v1/audit", s.handleAudit)
	s.Mux.HandleFunc("/api/v1/reports/", s.handleReports)
	s.Mux.HandleFunc("/api/v1/reconcile/sweep", s.handleReconcileSweep)
	fs := http.FileServer(http.Dir(s.Cfg.UIPath()))
	s.Mux.Handle("/", fs)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	st, err := s.Svc.Stats()
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, st)
}

func (s *Server) handleTenants(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		list, err := s.Store.ListTenants()
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"tenants": list})
	case http.MethodPost:
		var body struct {
			Name              string `json:"name"`
			Slug              string `json:"slug"`
			DeliveriesPerHour int    `json:"deliveries_per_hour"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
			return
		}
		if body.DeliveriesPerHour == 0 {
			body.DeliveriesPerHour = 100
		}
		t, err := s.Svc.CreateTenant(body.Name, body.Slug, body.DeliveriesPerHour)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, t)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleTenantsSub(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/tenants/")
	parts := splitPath(path)
	if len(parts) == 0 {
		http.NotFound(w, r)
		return
	}
	tenantID := parts[0]
	if len(parts) == 1 {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		t, err := s.Store.GetTenant(tenantID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, t)
		return
	}
	switch parts[1] {
	case "endpoints":
		s.handleTenantEndpoints(w, r, tenantID)
	case "events":
		s.handleTenantEvents(w, r, tenantID)
	default:
		http.NotFound(w, r)
	}
}

func (s *Server) handleTenantEndpoints(w http.ResponseWriter, r *http.Request, tenantID string) {
	switch r.Method {
	case http.MethodGet:
		list, err := s.Store.ListEndpoints(tenantID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"endpoints": list})
	case http.MethodPost:
		var body struct {
			Name        string `json:"name"`
			URL         string `json:"url"`
			HMACSecret  string `json:"hmac_secret"`
			Enabled     *bool  `json:"enabled"`
			MaxAttempts int    `json:"max_attempts"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
			return
		}
		enabled := true
		if body.Enabled != nil {
			enabled = *body.Enabled
		}
		if body.MaxAttempts == 0 {
			body.MaxAttempts = 5
		}
		ep, err := s.Svc.CreateEndpoint(tenantID, body.Name, body.URL, body.HMACSecret, enabled, body.MaxAttempts)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, ep)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleTenantEvents(w http.ResponseWriter, r *http.Request, tenantID string) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	status := r.URL.Query().Get("status")
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	list, err := s.Store.ListEvents(tenantID, status, limit)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"events": list})
}

func (s *Server) handleEndpointsSub(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/endpoints/")
	parts := splitPath(path)
	if len(parts) == 0 {
		http.NotFound(w, r)
		return
	}
	epID := parts[0]
	if len(parts) == 1 {
		switch r.Method {
		case http.MethodGet:
			ep, err := s.Store.GetEndpoint(epID)
			if err != nil {
				writeErr(w, err)
				return
			}
			writeJSON(w, http.StatusOK, ep)
		case http.MethodPatch:
			var body struct {
				Name        *string `json:"name"`
				URL         *string `json:"url"`
				HMACSecret  *string `json:"hmac_secret"`
				Enabled     *bool   `json:"enabled"`
				MaxAttempts *int    `json:"max_attempts"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
				return
			}
			ep, err := s.Store.PatchEndpoint(epID, body.Name, body.URL, body.HMACSecret, body.Enabled, body.MaxAttempts)
			if err != nil {
				writeErr(w, err)
				return
			}
			writeJSON(w, http.StatusOK, ep)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
		return
	}
	switch parts[1] {
	case "events":
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Payload        any     `json:"payload"`
			IdempotencyKey *string `json:"idempotency_key"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
			return
		}
		ev, created, err := s.Svc.Enqueue(epID, body.Payload, body.IdempotencyKey)
		if err != nil {
			writeErr(w, err)
			return
		}
		if created {
			writeJSON(w, http.StatusCreated, ev)
		} else {
			writeJSON(w, http.StatusOK, ev)
		}
	case "pause":
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		ep, err := s.Svc.Pause(epID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ep)
	case "resume":
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		ep, err := s.Svc.Resume(epID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ep)
	default:
		http.NotFound(w, r)
	}
}

func (s *Server) handleEventsSub(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/events/")
	parts := splitPath(path)
	if len(parts) == 0 {
		http.NotFound(w, r)
		return
	}
	eventID := parts[0]
	if len(parts) == 1 {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		ev, err := s.Store.GetEvent(eventID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ev)
		return
	}
	switch parts[1] {
	case "claim":
		s.handleClaim(w, r, eventID)
	case "complete":
		s.handleComplete(w, r, eventID)
	case "deliver":
		s.handleDeliver(w, r, eventID)
	case "replay":
		s.handleReplay(w, r, eventID)
	case "attempts":
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		list, err := s.Store.ListAttempts(eventID)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"attempts": list})
	default:
		http.NotFound(w, r)
	}
}

func (s *Server) handleClaim(w http.ResponseWriter, r *http.Request, eventID string) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		LeaseOwner   string `json:"lease_owner"`
		LeaseSeconds int    `json:"lease_seconds"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
		return
	}
	ev, err := s.Svc.Claim(eventID, body.LeaseOwner, body.LeaseSeconds)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, ev)
}

func (s *Server) handleComplete(w http.ResponseWriter, r *http.Request, eventID string) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		LeaseOwner string `json:"lease_owner"`
		Outcome    string `json:"outcome"`
		HTTPStatus int    `json:"http_status"`
		Error      string `json:"error"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
		return
	}
	ev, err := s.Svc.Complete(eventID, body.LeaseOwner, body.Outcome, body.HTTPStatus, body.Error)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, ev)
}

func (s *Server) handleDeliver(w http.ResponseWriter, r *http.Request, eventID string) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		LeaseOwner string `json:"lease_owner"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, errorBody{Error: "invalid_json"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()
	ev, err := s.Svc.Deliver(ctx, eventID, body.LeaseOwner)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, ev)
}

func (s *Server) handleReplay(w http.ResponseWriter, r *http.Request, eventID string) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	bearer := policy.BearerFromHeader(r.Header.Get("Authorization"))
	ev, err := s.Svc.Replay(eventID, bearer)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, ev)
}

func (s *Server) handleAudit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	list, err := s.Store.ListAudit(limit)
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"events": list})
}

func splitPath(p string) []string {
	p = strings.Trim(p, "/")
	if p == "" {
		return nil
	}
	return strings.Split(p, "/")
}
