package api

import (
	"net/http"
	"strings"

	"outbox/internal/reconcile"
	"outbox/internal/report"
)

func (s *Server) handleReports(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/reports/")
	switch path {
	case "tenants":
		list, err := report.TenantUsages(s.Store, s.Store.Now())
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"usages": list})
	case "dlq":
		list, err := reconcile.DLQByTenant(s.Store)
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"dlq": list})
	case "aging":
		list, err := reconcile.PendingAging(s.Store, s.Store.Now())
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"aging": list})
	default:
		if strings.HasPrefix(path, "endpoints/") {
			tenantID := strings.TrimPrefix(path, "endpoints/")
			list, err := report.EndpointHealthReport(s.Store, tenantID)
			if err != nil {
				writeErr(w, err)
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"endpoints": list})
			return
		}
		http.NotFound(w, r)
	}
}

func (s *Server) handleReconcileSweep(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	sw := &reconcile.Sweeper{Store: s.Store}
	res, err := sw.ExpireStaleLeases(s.Store.Now())
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, res)
}
