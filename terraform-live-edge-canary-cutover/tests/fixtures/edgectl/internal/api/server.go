// Package api exposes the live edge control-plane HTTP surface.
package api

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"

	"edgectl/internal/config"
	"edgectl/internal/store"
	"edgectl/internal/traffic"
)

// Server binds configuration, store, and traffic simulator to HTTP routes.
type Server struct {
	cfg *config.Config
	st  *store.Store
	sim *traffic.Simulator
	mux *http.ServeMux
}

// New builds the routed handler.
func New(cfg *config.Config, st *store.Store, sim *traffic.Simulator) http.Handler {
	s := &Server{cfg: cfg, st: st, sim: sim, mux: http.NewServeMux()}

	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	s.mux.HandleFunc("GET /v1/snapshot", s.handleSnapshot)
	s.mux.HandleFunc("GET /v1/metrics", s.handleMetrics)
	s.mux.HandleFunc("POST /v1/traffic/reset", s.handleTrafficReset)

	s.mux.HandleFunc("PUT /v1/networks/{id}", s.handlePutNetwork)
	s.mux.HandleFunc("PUT /v1/pools/{id}", s.handlePutPool)
	s.mux.HandleFunc("PUT /v1/canary/{id}", s.handlePutCanary)
	s.mux.HandleFunc("PUT /v1/waf/{id}", s.handlePutWAF)
	s.mux.HandleFunc("PUT /v1/tls/{id}", s.handlePutTLS)
	s.mux.HandleFunc("PUT /v1/dns/{zone}/{name}", s.handlePutDNS)

	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":        "ok",
		"config_digest": s.cfg.Digest,
	})
}

func (s *Server) handleSnapshot(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, s.st.Snapshot())
}

func (s *Server) handleMetrics(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, s.st.Metrics())
}

func (s *Server) handleTrafficReset(w http.ResponseWriter, _ *http.Request) {
	if err := s.st.ResetTraffic(); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "reset",
		"metrics": s.st.Metrics(),
	})
}

func (s *Server) handlePutNetwork(w http.ResponseWriter, r *http.Request) {
	var body store.Network
	if !decodeBody(w, r, &body) {
		return
	}
	id := r.PathValue("id")
	if body.ID == "" {
		body.ID = id
	} else if body.ID != id {
		writeError(w, http.StatusBadRequest, "id mismatch between path and body")
		return
	}
	if err := s.st.PutNetwork(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *Server) handlePutPool(w http.ResponseWriter, r *http.Request) {
	var body store.Pool
	if !decodeBody(w, r, &body) {
		return
	}
	id := r.PathValue("id")
	if body.ID == "" {
		body.ID = id
	} else if body.ID != id {
		writeError(w, http.StatusBadRequest, "id mismatch between path and body")
		return
	}
	if err := s.st.PutPool(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *Server) handlePutCanary(w http.ResponseWriter, r *http.Request) {
	var body store.Canary
	if !decodeBody(w, r, &body) {
		return
	}
	id := r.PathValue("id")
	if body.ID == "" {
		body.ID = id
	} else if body.ID != id {
		writeError(w, http.StatusBadRequest, "id mismatch between path and body")
		return
	}
	if err := s.st.PutCanary(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *Server) handlePutWAF(w http.ResponseWriter, r *http.Request) {
	var body store.WAF
	if !decodeBody(w, r, &body) {
		return
	}
	id := r.PathValue("id")
	if body.ID == "" {
		body.ID = id
	} else if body.ID != id {
		writeError(w, http.StatusBadRequest, "id mismatch between path and body")
		return
	}
	if err := s.st.PutWAF(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *Server) handlePutTLS(w http.ResponseWriter, r *http.Request) {
	var body store.TLSCert
	if !decodeBody(w, r, &body) {
		return
	}
	id := r.PathValue("id")
	if body.ID == "" {
		body.ID = id
	} else if body.ID != id {
		writeError(w, http.StatusBadRequest, "id mismatch between path and body")
		return
	}
	if err := s.st.PutTLS(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *Server) handlePutDNS(w http.ResponseWriter, r *http.Request) {
	var body store.DNSRecord
	if !decodeBody(w, r, &body) {
		return
	}
	zone := r.PathValue("zone")
	name := r.PathValue("name")
	if body.Zone == "" {
		body.Zone = zone
	} else if body.Zone != zone {
		writeError(w, http.StatusBadRequest, "zone mismatch between path and body")
		return
	}
	if body.Name == "" {
		body.Name = name
	} else if body.Name != name {
		writeError(w, http.StatusBadRequest, "name mismatch between path and body")
		return
	}
	if err := s.st.PutDNS(body); err != nil {
		writeStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, body)
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	_ = enc.Encode(body)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeStoreError(w http.ResponseWriter, err error) {
	var conflict *store.ConflictError
	var validation *store.ValidationError
	var notFound *store.NotFoundError
	switch {
	case errors.As(err, &conflict):
		writeError(w, http.StatusConflict, conflict.Msg)
	case errors.As(err, &validation):
		writeError(w, http.StatusBadRequest, validation.Msg)
	case errors.As(err, &notFound):
		writeError(w, http.StatusNotFound, notFound.Msg)
	default:
		writeError(w, http.StatusInternalServerError, err.Error())
	}
}

func decodeBody(w http.ResponseWriter, r *http.Request, dst any) bool {
	defer r.Body.Close()
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json body")
		return false
	}
	return true
}
