package main

import (
    "net/http"
    "strings"

    "routecp/internal/controlplane"
)

func registerOperationalRoutes(mux *http.ServeMux, s *server) {
    mux.HandleFunc("GET /readyz", s.ready)
    mux.HandleFunc("GET /v1/inventory", s.inventory)
    mux.HandleFunc("GET /v1/node-inventory", s.nodeInventory)
    mux.HandleFunc("POST /v1/trace", s.trace)
    mux.HandleFunc("GET /v1/tables", s.tables)
    mux.HandleFunc("GET /v1/topology", s.topology)
    mux.HandleFunc("GET /v1/dependencies", s.dependencies)
    mux.HandleFunc("GET /v1/policy", s.policy)
    mux.HandleFunc("POST /v1/safety/check", s.safetyCheck)
    mux.HandleFunc("POST /v1/impact", s.impact)
    mux.HandleFunc("GET /v1/transactions", s.transactions)
    mux.HandleFunc("GET /v1/recovery", s.recovery)
    mux.HandleFunc("GET /v1/audit/integrity", s.auditIntegrity)
    mux.HandleFunc("GET /v1/fleet/health", s.fleetHealth)
    mux.HandleFunc("POST /v1/rollouts/preview", s.rolloutPreview)
    mux.HandleFunc("GET /v1/management/reachability", s.managementReachability)
}

func (s *server) ready(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    health := s.cp.FleetHealth()
    status := http.StatusOK
    state := "ready"
    if health.Nodes > 0 && health.Online == 0 {
        status = http.StatusServiceUnavailable
        state = "degraded"
    }
    writeJSON(w, status, map[string]any{"status": state, "revision": health.Revision, "online_nodes": health.Online, "nodes": health.Nodes})
}

func (s *server) inventory(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    writeJSON(w, http.StatusOK, s.cp.Inventory())
}

func (s *server) nodeInventory(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    nodeID := strings.TrimSpace(r.URL.Query().Get("node"))
    if nodeID == "" {
        writeError(w, http.StatusBadRequest, errRequired("node"))
        return
    }
    item, err := s.cp.NodeInventory(nodeID)
    if err != nil {
        writeError(w, statusFor(err), err)
        return
    }
    writeJSON(w, http.StatusOK, item)
}

func (s *server) trace(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    var req controlplane.TraceRequest
    if err := decodeJSON(r, &req); err != nil {
        writeError(w, http.StatusBadRequest, err)
        return
    }
    result, err := s.cp.Trace(req)
    if err != nil {
        writeError(w, statusFor(err), err)
        return
    }
    writeJSON(w, http.StatusOK, result)
}

func (s *server) tables(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    nodeID := strings.TrimSpace(r.URL.Query().Get("node"))
    writeJSON(w, http.StatusOK, s.cp.RouteTables(nodeID))
}

func (s *server) topology(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    nodeID := strings.TrimSpace(r.URL.Query().Get("node"))
    writeJSON(w, http.StatusOK, s.cp.Topology(nodeID))
}

func (s *server) dependencies(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    nodeID := strings.TrimSpace(r.URL.Query().Get("node"))
    writeJSON(w, http.StatusOK, s.cp.Dependencies(nodeID))
}

func (s *server) policy(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    nodeID := strings.TrimSpace(r.URL.Query().Get("node"))
    writeJSON(w, http.StatusOK, s.cp.EvaluatePolicy(nodeID))
}

func (s *server) safetyCheck(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    var req controlplane.ChangeRequest
    if err := decodeJSON(r, &req); err != nil {
        writeError(w, http.StatusBadRequest, err)
        return
    }
    result, err := s.cp.CheckSafety(req)
    if err != nil {
        writeError(w, statusFor(err), err)
        return
    }
    writeJSON(w, http.StatusOK, result)
}

func (s *server) impact(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    var req controlplane.ChangeImpactRequest
    if err := decodeJSON(r, &req); err != nil {
        writeError(w, http.StatusBadRequest, err)
        return
    }
    result, err := s.cp.ChangeImpact(req)
    if err != nil {
        writeError(w, statusFor(err), err)
        return
    }
    writeJSON(w, http.StatusOK, result)
}

func (s *server) transactions(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    writeJSON(w, http.StatusOK, s.cp.Transactions())
}

func (s *server) recovery(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    writeJSON(w, http.StatusOK, s.cp.RecoveryPlan())
}

func (s *server) auditIntegrity(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    writeJSON(w, http.StatusOK, s.cp.AuditIntegrity())
}

func (s *server) fleetHealth(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    writeJSON(w, http.StatusOK, s.cp.FleetHealth())
}

func (s *server) rolloutPreview(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    var req controlplane.RolloutRequest
    if err := decodeJSON(r, &req); err != nil {
        writeError(w, http.StatusBadRequest, err)
        return
    }
    result, err := s.cp.PreviewRollout(req)
    if err != nil {
        writeError(w, statusFor(err), err)
        return
    }
    writeJSON(w, http.StatusOK, result)
}

func (s *server) managementReachability(w http.ResponseWriter, r *http.Request) {
    s.requests.Add(1)
    violations := s.cp.ManagementReachability()
    status := http.StatusOK
    if len(violations) > 0 { status = http.StatusServiceUnavailable }
    writeJSON(w, status, map[string]any{"reachable": len(violations) == 0, "violations": violations})
}

type requiredError string
func (e requiredError) Error() string { return string(e) + " is required" }
func errRequired(name string) error { return requiredError(name) }
