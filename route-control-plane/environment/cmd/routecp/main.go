package main

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "strconv"
    "strings"
    "sync/atomic"
    "syscall"
    "time"

    "routecp/internal/controlplane"
)

type server struct { cp *controlplane.ControlPlane; requests atomic.Uint64 }
type errorBody struct { Error string `json:"error"` }

func main() {
    cfg := controlplane.DefaultConfig()
    if v := strings.TrimSpace(os.Getenv("ROUTECP_STATE_DIR")); v != "" { cfg.StateDir = v }
    if v := strings.TrimSpace(os.Getenv("ROUTECP_PROTECTED_CIDRS")); v != "" { cfg.ProtectedCIDRs = splitCSV(v) }
    if v := strings.TrimSpace(os.Getenv("ROUTECP_MAX_WAVE")); v != "" {
        n, err := strconv.Atoi(v); if err != nil || n < 1 { log.Fatalf("invalid ROUTECP_MAX_WAVE: %q", v) }; cfg.MaxWave = n
    }
    cp, err := controlplane.Open(cfg); if err != nil { log.Fatalf("open control plane: %v", err) }
    srv := &server{cp: cp}
    mux := http.NewServeMux(); srv.routes(mux)
    addr := getenv("ROUTECP_LISTEN", ":8080")
    httpServer := &http.Server{Addr:addr,Handler:requestLog(mux),ReadHeaderTimeout:5*time.Second,ReadTimeout:30*time.Second,WriteTimeout:30*time.Second,IdleTimeout:90*time.Second}
    ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT); defer cancel()
    go func() { <-ctx.Done(); shutdown, done := context.WithTimeout(context.Background(), 10*time.Second); defer done(); _ = httpServer.Shutdown(shutdown) }()
    log.Printf("routecp listening on %s", addr)
    if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) { log.Fatalf("serve: %v", err) }
}

func (s *server) routes(mux *http.ServeMux) {
    mux.HandleFunc("GET /healthz", s.health)
    mux.HandleFunc("GET /v1/state", s.state)
    mux.HandleFunc("GET /v1/nodes", s.nodes)
    mux.HandleFunc("POST /v1/nodes", s.upsertNode)
    mux.HandleFunc("GET /v1/routes", s.listRoutes)
    mux.HandleFunc("POST /v1/revisions/preview", s.preview)
    mux.HandleFunc("POST /v1/revisions/apply", s.apply)
    mux.HandleFunc("POST /v1/revisions/rollback", s.rollback)
    mux.HandleFunc("GET /v1/drift", s.drift)
    mux.HandleFunc("POST /v1/reconcile", s.reconcile)
    mux.HandleFunc("POST /v1/rollouts", s.rollout)
    mux.HandleFunc("GET /v1/audit", s.audit)
    registerOperationalRoutes(mux, s)
    registerDiagnosticRoutes(mux, s)
}

func (s *server) health(w http.ResponseWriter, r *http.Request) { writeJSON(w,http.StatusOK,map[string]any{"status":"ok","revision":s.cp.Revision(),"requests":s.requests.Add(1)}) }
func (s *server) state(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Snapshot()) }
func (s *server) nodes(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Nodes()) }
func (s *server) upsertNode(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var node controlplane.Node; if err:=decodeJSON(r,&node); err!=nil { writeError(w,http.StatusBadRequest,err); return }; if err:=s.cp.UpsertNode(node); err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusAccepted,node) }
func (s *server) listRoutes(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Routes(strings.TrimSpace(r.URL.Query().Get("node")),strings.TrimSpace(r.URL.Query().Get("table")))) }
func (s *server) preview(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var req controlplane.ChangeRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; plan,err:=s.cp.Preview(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusOK,plan) }
func (s *server) apply(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var req controlplane.ApplyRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; txn,err:=s.cp.Apply(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusAccepted,txn) }
func (s *server) rollback(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var req controlplane.RollbackRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; txn,err:=s.cp.Rollback(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusAccepted,txn) }
func (s *server) drift(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); writeJSON(w,http.StatusOK,s.cp.Drift(strings.TrimSpace(r.URL.Query().Get("node")))) }
func (s *server) reconcile(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var req controlplane.ReconcileRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; result,err:=s.cp.Reconcile(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusAccepted,result) }
func (s *server) rollout(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); var req controlplane.RolloutRequest; if err:=decodeJSON(r,&req); err!=nil { writeError(w,http.StatusBadRequest,err); return }; result,err:=s.cp.Rollout(req); if err!=nil { writeError(w,statusFor(err),err); return }; writeJSON(w,http.StatusAccepted,result) }
func (s *server) audit(w http.ResponseWriter, r *http.Request) { s.requests.Add(1); limit:=100; if raw:=r.URL.Query().Get("limit"); raw!="" { if parsed,err:=strconv.Atoi(raw); err==nil && parsed>0 && parsed<=1000 { limit=parsed } }; writeJSON(w,http.StatusOK,s.cp.Audit(limit)) }

func decodeJSON(r *http.Request, dst any) error { if !strings.HasPrefix(strings.ToLower(r.Header.Get("Content-Type")),"application/json") { return fmt.Errorf("content-type must be application/json") }; dec:=json.NewDecoder(http.MaxBytesReader(nil,r.Body,2<<20)); dec.DisallowUnknownFields(); if err:=dec.Decode(dst); err!=nil { return fmt.Errorf("decode request: %w",err) }; return nil }
func writeJSON(w http.ResponseWriter,status int,value any) { w.Header().Set("Content-Type","application/json"); w.WriteHeader(status); _=json.NewEncoder(w).Encode(value) }
func writeError(w http.ResponseWriter,status int,err error) { writeJSON(w,status,errorBody{Error:err.Error()}) }
func statusFor(err error) int { switch { case errors.Is(err,controlplane.ErrConflict): return http.StatusConflict; case errors.Is(err,controlplane.ErrUnsafe): return http.StatusUnprocessableEntity; case errors.Is(err,controlplane.ErrNotFound): return http.StatusNotFound; default: return http.StatusBadRequest } }
func requestLog(next http.Handler) http.Handler { return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request) { started:=time.Now(); next.ServeHTTP(w,r); log.Printf("method=%s path=%s elapsed=%s",r.Method,r.URL.Path,time.Since(started)) }) }
func splitCSV(v string) []string { fields:=strings.Split(v,","); out:=make([]string,0,len(fields)); for _,field:=range fields { field=strings.TrimSpace(field); if field!="" { out=append(out,field) } }; return out }
func getenv(name,fallback string) string { if value:=strings.TrimSpace(os.Getenv(name)); value!="" { return value }; return fallback }
