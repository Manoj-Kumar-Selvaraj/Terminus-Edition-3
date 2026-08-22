package main

import (
    "net/http"
    "strings"
)

func registerDiagnosticRoutes(mux *http.ServeMux,s *server) {
    mux.HandleFunc("GET /v1/diagnostics",s.diagnostics)
    mux.HandleFunc("GET /v1/state-diff",s.stateDiff)
    mux.HandleFunc("POST /v1/path-matrix",s.pathMatrix)
}

func (s *server) diagnostics(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Diagnostics(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) stateDiff(w http.ResponseWriter,r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.StateDiff(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) pathMatrix(w http.ResponseWriter,r *http.Request) {
    s.requests.Add(1)
    var body struct { Destinations []string `json:"destinations"` }
    if err:=decodeJSON(r,&body); err!=nil { writeError(w,http.StatusBadRequest,err); return }
    result,err:=s.cp.PathMatrix(body.Destinations); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusOK,result)
}
