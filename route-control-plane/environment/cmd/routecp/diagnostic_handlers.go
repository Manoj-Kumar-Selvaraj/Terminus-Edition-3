package main

import (
    "net/http"
    "strconv"
    "strings"

    "routecp/internal/controlplane"
)

func registerDiagnosticRoutes(mux *http.ServeMux,s *server) {
    mux.HandleFunc("GET /v1/diagnostics",s.diagnostics)
    mux.HandleFunc("GET /v1/state-diff",s.stateDiff)
    mux.HandleFunc("POST /v1/path-matrix",s.pathMatrix)
    mux.HandleFunc("GET /v1/route-analysis",s.routeAnalysis)
    mux.HandleFunc("GET /v1/prefix-coverage",s.prefixCoverage)
    mux.HandleFunc("GET /v1/consistency",s.consistency)
    mux.HandleFunc("POST /v1/change-window",s.changeWindow)
}

func (s *server) diagnostics(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Diagnostics(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) stateDiff(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.StateDiff(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) pathMatrix(w http.ResponseWriter,r *http.Request) {
    s.requests.Add(1)
    var body struct { Destinations []string `json:"destinations"` }
    if err:=decodeJSON(r,&body); err!=nil { writeError(w,http.StatusBadRequest,err); return }
    result,err:=s.cp.PathMatrix(body.Destinations); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusOK,result)
}
func (s *server) routeAnalysis(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.AnalyzeRoutes(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) prefixCoverage(w http.ResponseWriter,r *http.Request) {
    s.requests.Add(1); table:=0; if raw:=strings.TrimSpace(r.URL.Query().Get("table")); raw!="" { if parsed,err:=strconv.Atoi(raw); err==nil { table=parsed } }
    writeJSON(w,http.StatusOK,s.cp.PrefixCoverage(strings.TrimSpace(r.URL.Query().Get("node")),table))
}
func (s *server) consistency(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Consistency()) }
func (s *server) changeWindow(w http.ResponseWriter,r *http.Request) {
    s.requests.Add(1); var req controlplane.ChangeWindowRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; result,err:=s.cp.PlanChangeWindow(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusOK,result)
}
