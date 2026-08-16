package api

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"stackyard/internal/audit"
	"stackyard/internal/config"
	"stackyard/internal/model"
	"stackyard/internal/policy"
	"stackyard/internal/runner"
	"stackyard/internal/store"
)

type Server struct {
	Cfg    config.Config
	Store  *store.Store
	Audit  *audit.Writer
	Runner *runner.Executor
	Mux    *http.ServeMux
}

func New(cfg config.Config, st *store.Store) *Server {
	s := &Server{Cfg: cfg, Store: st, Mux: http.NewServeMux()}
	s.Audit = &audit.Writer{
		Insert: st.InsertAudit,
		NewID:  func() string { return newID("aud_") },
	}
	s.Runner = &runner.Executor{
		Store:        st,
		DataDir:      cfg.DataDir,
		TerraformBin: cfg.TerraformBin,
		Audit: func(ctx context.Context, workspaceID, action, detail, actor string) error {
			return s.Audit.Record(ctx, workspaceID, action, detail, actor)
		},
	}
	s.routes()
	return s
}

func newID(prefix string) string {
	var b [8]byte
	_, _ = rand.Read(b[:])
	return prefix + hex.EncodeToString(b[:])
}

func (s *Server) routes() {
	s.Mux.HandleFunc("GET /api/v1/health", s.handleHealth)
	s.Mux.HandleFunc("GET /api/v1/orgs", s.handleListOrgs)
	s.Mux.HandleFunc("POST /api/v1/orgs", s.handleCreateOrg)
	s.Mux.HandleFunc("GET /api/v1/orgs/{org_id}", s.handleGetOrg)
	s.Mux.HandleFunc("GET /api/v1/orgs/{org_id}/workspaces", s.handleListWorkspaces)
	s.Mux.HandleFunc("POST /api/v1/orgs/{org_id}/workspaces", s.handleCreateWorkspace)
	s.Mux.HandleFunc("GET /api/v1/workspaces/{workspace_id}", s.handleGetWorkspace)
	s.Mux.HandleFunc("DELETE /api/v1/workspaces/{workspace_id}", s.handleDeleteWorkspace)
	s.Mux.HandleFunc("GET /api/v1/workspaces/{workspace_id}/vars", s.handleListVars)
	s.Mux.HandleFunc("POST /api/v1/workspaces/{workspace_id}/vars", s.handleCreateVar)
	s.Mux.HandleFunc("GET /api/v1/vars/{var_id}", s.handleGetVar)
	s.Mux.HandleFunc("DELETE /api/v1/vars/{var_id}", s.handleDeleteVar)
	s.Mux.HandleFunc("GET /api/v1/workspaces/{workspace_id}/runs", s.handleListRuns)
	s.Mux.HandleFunc("POST /api/v1/workspaces/{workspace_id}/runs", s.handleCreateRun)
	s.Mux.HandleFunc("GET /api/v1/runs/{run_id}", s.handleGetRun)
	s.Mux.HandleFunc("POST /api/v1/runs/{run_id}/discard", s.handleDiscardRun)
	s.Mux.HandleFunc("POST /api/v1/runs/{run_id}/cancel", s.handleCancelRun)
	s.Mux.HandleFunc("POST /api/v1/workspaces/{workspace_id}/lock", s.handleLock)
	s.Mux.HandleFunc("POST /api/v1/workspaces/{workspace_id}/unlock", s.handleUnlock)
	s.Mux.HandleFunc("GET /api/v1/workspaces/{workspace_id}/lock", s.handleGetLock)
	s.Mux.HandleFunc("GET /api/v1/workspaces/{workspace_id}/audit", s.handleListAudit)
	s.Mux.Handle("/", s.staticHandler())
}

func (s *Server) Handler() http.Handler {
	return s.authMiddleware(s.Mux)
}

func (s *Server) authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.Cfg.Token == "" {
			next.ServeHTTP(w, r)
			return
		}
		path := r.URL.Path
		if path == "/api/v1/health" || path == "/" || strings.HasPrefix(path, "/css/") ||
			strings.HasPrefix(path, "/js/") || path == "/index.html" {
			next.ServeHTTP(w, r)
			return
		}
		if r.Header.Get("Authorization") != "Bearer "+s.Cfg.Token {
			writeErr(w, http.StatusUnauthorized, "unauthorized")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) staticHandler() http.Handler {
	fs := http.FileServer(http.Dir(s.Cfg.UIDir))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/api/") {
			writeErr(w, http.StatusNotFound, "not found")
			return
		}
		fs.ServeHTTP(w, r)
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if status == http.StatusNoContent {
		return
	}
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func decodeJSON(r *http.Request, dst any) error {
	defer r.Body.Close()
	return json.NewDecoder(r.Body).Decode(dst)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleListOrgs(w http.ResponseWriter, r *http.Request) {
	orgs, err := s.Store.ListOrgs(r.Context())
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if orgs == nil {
		orgs = []model.Org{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"orgs": orgs})
}

func (s *Server) handleCreateOrg(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name string `json:"name"`
		Slug string `json:"slug"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Name == "" || body.Slug == "" {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	org, err := s.Store.CreateOrg(r.Context(), body.Name, body.Slug, newID("org_"))
	if err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, org)
}

func (s *Server) handleGetOrg(w http.ResponseWriter, r *http.Request) {
	org, err := s.Store.GetOrg(r.Context(), r.PathValue("org_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	writeJSON(w, http.StatusOK, org)
}

func (s *Server) handleListWorkspaces(w http.ResponseWriter, r *http.Request) {
	list, err := s.Store.ListWorkspaces(r.Context(), r.PathValue("org_id"))
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if list == nil {
		list = []model.Workspace{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"workspaces": list})
}

func (s *Server) handleCreateWorkspace(w http.ResponseWriter, r *http.Request) {
	orgID := r.PathValue("org_id")
	if _, err := s.Store.GetOrg(r.Context(), orgID); err != nil {
		writeErr(w, http.StatusNotFound, "org not found")
		return
	}
	var body struct {
		Name             string `json:"name"`
		WorkingDirectory string `json:"working_directory"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Name == "" {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	ws, err := s.Store.CreateWorkspace(r.Context(), orgID, body.Name, body.WorkingDirectory, newID("ws_"))
	if err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	_ = os.MkdirAll(filepath.Join(s.Cfg.DataDir, ws.ID, ws.WorkingDirectory), 0o755)
	writeJSON(w, http.StatusCreated, ws)
}

func (s *Server) handleGetWorkspace(w http.ResponseWriter, r *http.Request) {
	ws, err := s.Store.GetWorkspace(r.Context(), r.PathValue("workspace_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	writeJSON(w, http.StatusOK, ws)
}

func (s *Server) handleDeleteWorkspace(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("workspace_id")
	ws, err := s.Store.GetWorkspace(r.Context(), id)
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	active, err := s.Store.CountNonTerminalRuns(r.Context(), id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := policy.CanDeleteWorkspace(ws.Locked, active); err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	if err := s.Store.DeleteWorkspace(r.Context(), id); err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func presentVar(v *model.Variable) model.Variable {
	out := *v
	out.Value = policy.RedactVariableValue(v.Sensitive, v.RawValue)
	return out
}

func (s *Server) handleListVars(w http.ResponseWriter, r *http.Request) {
	list, err := s.Store.ListVariables(r.Context(), r.PathValue("workspace_id"))
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	out := make([]model.Variable, 0, len(list))
	for i := range list {
		out = append(out, presentVar(&list[i]))
	}
	writeJSON(w, http.StatusOK, map[string]any{"vars": out})
}

func (s *Server) handleCreateVar(w http.ResponseWriter, r *http.Request) {
	wsID := r.PathValue("workspace_id")
	if _, err := s.Store.GetWorkspace(r.Context(), wsID); err != nil {
		writeErr(w, http.StatusNotFound, "workspace not found")
		return
	}
	var body struct {
		Key       string `json:"key"`
		Value     string `json:"value"`
		Sensitive bool   `json:"sensitive"`
		Category  string `json:"category"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Key == "" ||
		(body.Category != model.CategoryTerraform && body.Category != model.CategoryEnv) {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	v := model.Variable{
		ID:          newID("var_"),
		WorkspaceID: wsID,
		Key:         body.Key,
		RawValue:    body.Value,
		Sensitive:   body.Sensitive,
		Category:    body.Category,
		CreatedAt:   time.Now().UTC(),
	}
	created, err := s.Store.CreateVariable(r.Context(), v)
	if err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, presentVar(created))
}

func (s *Server) handleGetVar(w http.ResponseWriter, r *http.Request) {
	v, err := s.Store.GetVariable(r.Context(), r.PathValue("var_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	writeJSON(w, http.StatusOK, presentVar(v))
}

func (s *Server) handleDeleteVar(w http.ResponseWriter, r *http.Request) {
	if err := s.Store.DeleteVariable(r.Context(), r.PathValue("var_id")); err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) handleListRuns(w http.ResponseWriter, r *http.Request) {
	list, err := s.Store.ListRuns(r.Context(), r.PathValue("workspace_id"))
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if list == nil {
		list = []model.Run{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"runs": list})
}

func (s *Server) handleCreateRun(w http.ResponseWriter, r *http.Request) {
	wsID := r.PathValue("workspace_id")
	ws, err := s.Store.GetWorkspace(r.Context(), wsID)
	if err != nil {
		writeErr(w, http.StatusNotFound, "workspace not found")
		return
	}
	var body struct {
		Command string `json:"command"`
		Message string `json:"message"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Command == "" {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	active, err := s.Store.CountNonTerminalRuns(r.Context(), wsID)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := policy.CanCreateRun(active, body.Command, ws.Locked); err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	now := time.Now().UTC()
	run := model.Run{
		ID:          newID("run_"),
		WorkspaceID: wsID,
		Command:     body.Command,
		Status:      model.StatusQueued,
		Message:     body.Message,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	created, err := s.Store.CreateRun(r.Context(), run)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = s.Audit.Record(r.Context(), wsID, model.AuditRunCreated, body.Command, "api")
	if s.Cfg.SyncRuns {
		_ = s.Runner.Execute(r.Context(), created.ID)
		created, _ = s.Store.GetRun(r.Context(), created.ID)
	} else {
		go func(id string) {
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
			defer cancel()
			_ = s.Runner.Execute(ctx, id)
		}(created.ID)
	}
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleGetRun(w http.ResponseWriter, r *http.Request) {
	run, err := s.Store.GetRun(r.Context(), r.PathValue("run_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	writeJSON(w, http.StatusOK, run)
}

func (s *Server) handleDiscardRun(w http.ResponseWriter, r *http.Request) {
	run, err := s.Store.GetRun(r.Context(), r.PathValue("run_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	if err := policy.CanDiscard(run.Status); err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	from := run.Status
	run.Status = model.StatusDiscarded
	if err := s.Store.UpdateRun(r.Context(), *run); err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = s.Audit.Record(r.Context(), run.WorkspaceID, model.AuditRunStatus, from+"->"+model.StatusDiscarded, "api")
	run, _ = s.Store.GetRun(r.Context(), run.ID)
	writeJSON(w, http.StatusOK, run)
}

func (s *Server) handleCancelRun(w http.ResponseWriter, r *http.Request) {
	run, err := s.Store.GetRun(r.Context(), r.PathValue("run_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	if err := policy.CanCancel(run.Status); err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	from := run.Status
	run.Status = model.StatusCanceled
	if err := s.Store.UpdateRun(r.Context(), *run); err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = s.Audit.Record(r.Context(), run.WorkspaceID, model.AuditRunStatus, from+"->"+model.StatusCanceled, "api")
	run, _ = s.Store.GetRun(r.Context(), run.ID)
	writeJSON(w, http.StatusOK, run)
}

func (s *Server) handleLock(w http.ResponseWriter, r *http.Request) {
	wsID := r.PathValue("workspace_id")
	if _, err := s.Store.GetWorkspace(r.Context(), wsID); err != nil {
		writeErr(w, http.StatusNotFound, "workspace not found")
		return
	}
	if _, err := s.Store.GetLock(r.Context(), wsID); err == nil {
		writeErr(w, http.StatusConflict, policy.ErrAlreadyLocked.Error())
		return
	} else if err != nil && !errors.Is(err, sql.ErrNoRows) {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	var body struct {
		Holder string `json:"holder"`
		Reason string `json:"reason"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Holder == "" {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	lock := model.Lock{
		ID:          newID("lock_"),
		WorkspaceID: wsID,
		Holder:      body.Holder,
		Reason:      body.Reason,
		CreatedAt:   time.Now().UTC(),
	}
	created, err := s.Store.CreateLock(r.Context(), lock)
	if err != nil {
		writeErr(w, http.StatusConflict, policy.ErrAlreadyLocked.Error())
		return
	}
	_ = s.Audit.Record(r.Context(), wsID, model.AuditLockAcquire, body.Holder, "api")
	writeJSON(w, http.StatusCreated, created)
}

func (s *Server) handleUnlock(w http.ResponseWriter, r *http.Request) {
	wsID := r.PathValue("workspace_id")
	lock, err := s.Store.GetLock(r.Context(), wsID)
	if err != nil {
		writeErr(w, http.StatusNotFound, "not locked")
		return
	}
	var body struct {
		Holder string `json:"holder"`
	}
	if err := decodeJSON(r, &body); err != nil || body.Holder == "" {
		writeErr(w, http.StatusBadRequest, "invalid body")
		return
	}
	if err := policy.CanUnlock(lock.Holder, body.Holder); err != nil {
		writeErr(w, http.StatusForbidden, err.Error())
		return
	}
	if err := s.Store.DeleteLock(r.Context(), wsID); err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = s.Audit.Record(r.Context(), wsID, model.AuditLockRelease, body.Holder, "api")
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) handleGetLock(w http.ResponseWriter, r *http.Request) {
	lock, err := s.Store.GetLock(r.Context(), r.PathValue("workspace_id"))
	if err != nil {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	writeJSON(w, http.StatusOK, lock)
}

func (s *Server) handleListAudit(w http.ResponseWriter, r *http.Request) {
	events, err := s.Store.ListAudit(r.Context(), r.PathValue("workspace_id"))
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	if events == nil {
		events = []model.AuditEvent{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"events": events})
}
