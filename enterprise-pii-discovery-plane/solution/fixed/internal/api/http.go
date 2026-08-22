package api

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strings"

	"enterprise-pii/internal/model"
	"enterprise-pii/internal/service"
)

type Server struct{Service *service.Service}
func (s *Server) Handler()http.Handler{mux:=http.NewServeMux();mux.HandleFunc("GET /health",s.health);mux.HandleFunc("GET /ready",s.ready);mux.HandleFunc("GET /v1/status",s.status);mux.HandleFunc("GET /v1/sources",s.sources);mux.HandleFunc("GET /v1/policies",s.policies);mux.HandleFunc("POST /v1/jobs",s.createJob);mux.HandleFunc("POST /v1/jobs/{id}/cancel",s.cancelJob);mux.HandleFunc("GET /v1/jobs/{id}",s.job);mux.HandleFunc("POST /v1/workers/register",s.registerWorker);mux.HandleFunc("POST /v1/workers/heartbeat",s.heartbeat);mux.HandleFunc("POST /v1/workers/lease",s.issueLease);mux.HandleFunc("POST /v1/workers/renew",s.renewLease);mux.HandleFunc("POST /v1/results",s.ingest);mux.HandleFunc("GET /v1/reports/{id}",s.report);mux.HandleFunc("POST /v1/reports/{id}/publish",s.publishReport);mux.HandleFunc("GET /v1/reports/{id}/export",s.export);return limitBody(mux)}
func write(w http.ResponseWriter,status int,value any){w.Header().Set("Content-Type","application/json");w.WriteHeader(status);_ = json.NewEncoder(w).Encode(value)}
func fail(w http.ResponseWriter,status int,err error){write(w,status,map[string]string{"error":err.Error()})}
func (s *Server) health(w http.ResponseWriter,r *http.Request){write(w,200,map[string]bool{"ok":true})}
func (s *Server) ready(w http.ResponseWriter,r *http.Request){value:=s.Service.Readiness();status:=200;if !value.Ready{status=503};write(w,status,value)}
func (s *Server) status(w http.ResponseWriter,r *http.Request){write(w,200,s.Service.Status())}
func (s *Server) sources(w http.ResponseWriter,r *http.Request){write(w,200,s.Service.Sources.List())}
func (s *Server) policies(w http.ResponseWriter,r *http.Request){write(w,200,s.Service.Policies.List())}
func (s *Server) createJob(w http.ResponseWriter,r *http.Request){var request struct{ID string `json:"id"`;PolicyVersion string `json:"policy_version"`;CorpusDigest string `json:"corpus_digest"`};if json.NewDecoder(r.Body).Decode(&request)!=nil{fail(w,400,errInvalid);return};job,err:=s.Service.CreateJob(principalFromRequest(r,s.Service.Config.TenantID),request.ID,request.PolicyVersion,request.CorpusDigest);if err!=nil{fail(w,409,err);return};write(w,201,job)}
func (s *Server) cancelJob(w http.ResponseWriter,r *http.Request){err:=s.Service.CancelJob(principalFromRequest(r,s.Service.Config.TenantID),r.PathValue("id"));if err!=nil{fail(w,409,err);return};write(w,200,map[string]string{"status":"cancelled"})}
func (s *Server) job(w http.ResponseWriter,r *http.Request){job,ok:=s.Service.Scheduler.Job(r.PathValue("id"));if !ok{fail(w,404,errMissing);return};write(w,200,map[string]any{"job":job,"shards":s.Service.Scheduler.Shards(job.ID)})}
func (s *Server) registerWorker(w http.ResponseWriter,r *http.Request){var worker model.WorkerSession;if json.NewDecoder(r.Body).Decode(&worker)!=nil{fail(w,400,errInvalid);return};registered,err:=s.Service.RegisterWorker(worker);if err!=nil{fail(w,409,err);return};write(w,201,registered)}
func (s *Server) heartbeat(w http.ResponseWriter,r *http.Request){var request struct{WorkerID string `json:"worker_id"`;SessionID string `json:"session_id"`};if json.NewDecoder(r.Body).Decode(&request)!=nil{fail(w,400,errInvalid);return};if err:=s.Service.Heartbeat(request.WorkerID,request.SessionID);err!=nil{fail(w,409,err);return};write(w,200,map[string]string{"status":"current"})}
func (s *Server) issueLease(w http.ResponseWriter,r *http.Request){var request struct{WorkerID string `json:"worker_id"`;SessionID string `json:"session_id"`};if json.NewDecoder(r.Body).Decode(&request)!=nil{fail(w,400,errInvalid);return};lease,err:=s.Service.IssueLease(request.WorkerID,request.SessionID);if err!=nil{fail(w,409,err);return};write(w,200,lease)}
func (s *Server) renewLease(w http.ResponseWriter,r *http.Request){var lease model.Lease;if json.NewDecoder(r.Body).Decode(&lease)!=nil{fail(w,400,errInvalid);return};renewed,err:=s.Service.RenewLease(lease);if err!=nil{fail(w,409,err);return};write(w,200,renewed)}
func (s *Server) ingest(w http.ResponseWriter,r *http.Request){var request struct{Lease model.Lease `json:"lease"`;Batch model.ResultBatch `json:"batch"`};if json.NewDecoder(r.Body).Decode(&request)!=nil{fail(w,400,errInvalid);return};receipt,replay,err:=s.Service.Ingest(request.Lease,request.Batch);if err!=nil{fail(w,409,err);return};write(w,200,map[string]any{"receipt":receipt,"replay":replay})}
func (s *Server) report(w http.ResponseWriter,r *http.Request){value,err:=s.Service.Report(principalFromRequest(r,s.Service.Config.TenantID),r.PathValue("id"));if err!=nil{fail(w,409,err);return};write(w,200,value)}
func (s *Server) publishReport(w http.ResponseWriter,r *http.Request){value,err:=s.Service.PublishReport(principalFromRequest(r,s.Service.Config.TenantID),r.PathValue("id"));if err!=nil{fail(w,409,err);return};write(w,201,value)}
func (s *Server) export(w http.ResponseWriter,r *http.Request){format:=strings.ToLower(r.URL.Query().Get("format"));body,err:=s.Service.Export(principalFromRequest(r,s.Service.Config.TenantID),r.PathValue("id"),format);if err!=nil{fail(w,409,err);return};if format=="csv"{w.Header().Set("Content-Type","text/csv")};_,_=w.Write(body)}
func principalFromRequest(r *http.Request, tenant string) model.Principal {
	if encoded := r.Header.Get("X-PII-Principal"); encoded != "" {
		body, err := base64.StdEncoding.DecodeString(encoded)
		if err == nil {
			var principal model.Principal
			if json.Unmarshal(body, &principal) == nil && principal.Tenant != "" {
				return principal
			}
		}
	}
	return service.AdminPrincipal(tenant)
}
func limitBody(next http.Handler)http.Handler{return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){r.Body=http.MaxBytesReader(w,r.Body,1<<20);next.ServeHTTP(w,r)})}
type staticError string
func (e staticError)Error()string{return string(e)}
const errInvalid staticError="invalid request"
const errMissing staticError="resource not found"
