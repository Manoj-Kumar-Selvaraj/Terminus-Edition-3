package service

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"time"

	"enterprise-pii/internal/auth"
	"enterprise-pii/internal/ingest"
	"enterprise-pii/internal/model"
	"enterprise-pii/internal/observe"
	"enterprise-pii/internal/persistence"
	"enterprise-pii/internal/registry"
	"enterprise-pii/internal/report"
	"enterprise-pii/internal/scheduler"
)

type Config struct { TenantID string `json:"tenant_id"`; Listen string `json:"listen"`; StateDir string `json:"state_dir"`; ReportDir string `json:"report_dir"`; CorpusDir string `json:"corpus_dir"`; PolicyFile string `json:"policy_file"`; SourceFile string `json:"source_file"`; WorkerTimeoutSeconds int `json:"worker_timeout_seconds"`; LeaseSeconds int `json:"lease_seconds"`; RetainedGenerations int `json:"retained_generations"`; RequiredWorkers int `json:"required_workers"`; AuditCapacity int `json:"audit_capacity"`; MetricSeriesCapacity int `json:"metric_series_capacity"` }
type sourceDocument struct { Generation string `json:"generation"`; Sources []model.Source `json:"sources"` }
type Service struct { Config Config; Sources *registry.SourceRegistry; Policies *registry.PolicyRegistry; Scheduler *scheduler.Scheduler; Results *ingest.Store; State *persistence.Store; Publisher *report.Publisher; Audit *observe.AuditLog; Metrics *observe.Metrics; Recovered bool; available map[string]bool }

func Load(configPath string)(*Service,error){body,err:=os.ReadFile(configPath);if err!=nil{return nil,err};var config Config;if json.Unmarshal(body,&config)!=nil{return nil,errors.New("invalid system config")};svc:=&Service{Config:config,Sources:registry.NewSourceRegistry(),Policies:registry.NewPolicyRegistry(),Scheduler:scheduler.New(time.Duration(config.LeaseSeconds)*time.Second),Results:ingest.New(),State:persistence.New(config.StateDir,config.RetainedGenerations),Publisher:report.NewPublisher(config.ReportDir),Audit:observe.NewAudit(config.AuditCapacity),Metrics:observe.NewMetrics(config.MetricSeriesCapacity),available:map[string]bool{}};if err=svc.loadSources();err!=nil{return nil,err};if err=svc.loadPolicy();err!=nil{return nil,err};return svc,nil}
func (s *Service) loadSources()error{body,err:=os.ReadFile(s.Config.SourceFile);if err!=nil{return err};var document sourceDocument;if json.Unmarshal(body,&document)!=nil{return errors.New("invalid source registry")};for _,source:=range document.Sources{source.Generation=document.Generation;registered,err:=s.Sources.Register(source);if err!=nil{return err};if info,err:=os.Stat(registered.CanonicalRoot);err==nil&&info.IsDir(){s.available[registered.ID]=true}};return nil}
func (s *Service) loadPolicy()error{body,err:=os.ReadFile(s.Config.PolicyFile);if err!=nil{return err};var policy model.Policy;if json.Unmarshal(body,&policy)!=nil{return errors.New("invalid policy")};_,err=s.Policies.Publish(policy,time.Now());return err}
func (s *Service) Recover()error{_,_,err:=s.State.Recover();if err!=nil{if os.IsNotExist(err){s.Recovered=true;return nil};return err};s.Recovered=true;s.Audit.Append(model.AuditEvent{Actor:"system",Action:"recover",Resource:"state",Outcome:"accepted"});return nil}
func (s *Service) CreateJob(principal model.Principal,id,policyVersion,corpusDigest string)(model.Job,error){policy,ok:=s.Policies.Get(policyVersion);if !ok{return model.Job{},errors.New("policy not found")};sources:=auth.New(s.Sources.List()).Sources(principal,"scan");if len(sources)==0{return model.Job{},errors.New("no authorized sources")};job:=model.Job{ID:id,Tenant:s.Config.TenantID,Generation:uint64(time.Now().UnixNano()),PolicyVersion:policy.Version,PolicyDigest:policy.Digest,DetectorBundle:policy.DetectorBundle,CorpusDigest:corpusDigest,SourceGeneration:sources[0].Generation};_,err:=s.Scheduler.CreateJob(job,sources,time.Now());if err==nil{err=s.Scheduler.Start(id,time.Now())};stored,_:=s.Scheduler.Job(id);s.Audit.Append(model.AuditEvent{Actor:principal.ID,Action:"job.create",Resource:id,Outcome:outcome(err)});return stored,err}
func (s *Service) CancelJob(principal model.Principal,id string)error{if !contains(principal.Actions,"cancel"){return errors.New("forbidden")};err:=s.Scheduler.Cancel(id,time.Now());s.Audit.Append(model.AuditEvent{Actor:principal.ID,Action:"job.cancel",Resource:id,Outcome:outcome(err)});return err}
func (s *Service) RegisterWorker(worker model.WorkerSession)(model.WorkerSession,error){registered,err:=s.Scheduler.RegisterWorker(worker,time.Now());s.Audit.Append(model.AuditEvent{Actor:worker.WorkerID,Action:"worker.register",Resource:worker.SessionID,Outcome:outcome(err)});s.Metrics.Add("worker_registrations_total",map[string]string{"outcome":outcome(err)},1);return registered,err}
func (s *Service) Heartbeat(workerID,sessionID string)error{err:=s.Scheduler.Heartbeat(workerID,sessionID,time.Now());s.Metrics.Add("worker_heartbeats_total",map[string]string{"outcome":outcome(err)},1);return err}
func (s *Service) IssueLease(workerID,sessionID string)(model.Lease,error){s.Scheduler.Expire(time.Now());lease,err:=s.Scheduler.Issue(workerID,sessionID,time.Now());s.Audit.Append(model.AuditEvent{Actor:workerID,Action:"lease.issue",Resource:lease.ShardID,Outcome:outcome(err)});s.Metrics.Add("leases_total",map[string]string{"outcome":outcome(err)},1);return lease,err}
func (s *Service) RenewLease(lease model.Lease)(model.Lease,error){renewed,err:=s.Scheduler.Renew(lease,time.Now());s.Metrics.Add("lease_renewals_total",map[string]string{"outcome":outcome(err)},1);return renewed,err}
func (s *Service) Ingest(lease model.Lease,batch model.ResultBatch)(ingest.BatchReceipt,bool,error){if err:=s.Scheduler.Validate(lease,time.Now());err!=nil{return ingest.BatchReceipt{},false,err};receipt,replay,err:=s.Results.Accept(batch);if err==nil&&batch.Complete&&!replay{err=s.Scheduler.Commit(batch.ShardID,batch.NextCheckpoint,batch.Sequence)};s.Metrics.Add("result_batches_total",map[string]string{"outcome":outcome(err)},1);return receipt,replay,err}
func (s *Service) Report(principal model.Principal,jobID string)(report.Report,error){job,ok:=s.Scheduler.Job(jobID);if !ok{return report.Report{},errors.New("job not found")};authorizer:=auth.New(s.Sources.List());visibleSources:=authorizer.Sources(principal,"report");visibleFindings:=authorizer.Findings(principal,"report",s.Results.Findings());return report.Aggregate(job,s.Scheduler.Shards(jobID),visibleSources,visibleFindings,s.Results.Errors(),s.Results.Truncations())}
func (s *Service) PublishReport(principal model.Principal,jobID string)(report.Manifest,error){value,err:=s.Report(principal,jobID);if err!=nil{return report.Manifest{},err};manifest,err:=s.Publisher.Publish(value);s.Audit.Append(model.AuditEvent{Actor:principal.ID,Action:"report.publish",Resource:jobID,Outcome:outcome(err)});return manifest,err}
func (s *Service) Export(principal model.Principal,jobID,format string)([]byte,error){value,err:=s.Report(principal,jobID);if err!=nil{return nil,err};if format=="json"{return report.JSON(value)};if format=="csv"{return report.CSV(value)};return nil,errors.New("unsupported export format")}
func (s *Service) Readiness()observe.Readiness{return observe.Evaluate(s.Recovered,s.Sources.List(),s.available,s.Scheduler.Workers(),s.Config.RequiredWorkers,time.Now())}
func (s *Service) Status()map[string]any{events,droppedAudit:=s.Audit.Snapshot();metrics,droppedMetrics:=s.Metrics.Snapshot();return map[string]any{"readiness":s.Readiness(),"workers":s.Scheduler.Workers(),"policies":s.Policies.List(),"sources":s.Sources.List(),"audit_events":events,"audit_dropped":droppedAudit,"metrics":metrics,"metric_series_dropped":droppedMetrics}}
func outcome(err error)string{if err!=nil{return "rejected"};return "accepted"}
func contains(items []string,value string)bool{for _,item:=range items{if item=="*"||item==value{return true}};return false}
func AdminPrincipal(tenant string)model.Principal{return model.Principal{ID:"local-admin",Tenant:tenant,Departments:[]string{"*"},Regions:[]string{"*"},Sources:[]string{"*"},Actions:[]string{"*"}}}
func NewID(prefix string)string{return fmt.Sprintf("%s-%d",prefix,time.Now().UTC().UnixNano())}
