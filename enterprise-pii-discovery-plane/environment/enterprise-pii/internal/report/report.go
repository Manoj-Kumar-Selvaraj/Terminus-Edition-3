package report

import (
	"bytes"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sort"
	"strconv"

	"enterprise-pii/internal/model"
)

type SummaryKey struct { Category string `json:"category"`; Confidence string `json:"confidence"`; SourceID string `json:"source_id"`; Department string `json:"department"`; Region string `json:"region"`; Priority string `json:"priority"` }
type SummaryRow struct { Key SummaryKey `json:"key"`; Findings int `json:"findings"`; Suppressed int `json:"suppressed"`; DistinctFingerprints int `json:"distinct_fingerprints"` }
type Completeness struct { Complete bool `json:"complete"`; Committed int `json:"committed"`; Skipped int `json:"skipped"`; Failed int `json:"failed"`; Missing int `json:"missing"`; Errors int `json:"errors"`; Truncations int `json:"truncations"` }
type Report struct { Schema string `json:"schema"`; Tenant string `json:"tenant"`; JobID string `json:"job_id"`; Generation uint64 `json:"generation"`; PolicyVersion string `json:"policy_version"`; PolicyDigest string `json:"policy_digest"`; CorpusDigest string `json:"corpus_digest"`; Completeness Completeness `json:"completeness"`; Rows []SummaryRow `json:"rows"`; Examples []model.Finding `json:"examples"` }
type FileDigest struct { Name string `json:"name"`; Bytes int `json:"bytes"`; SHA256 string `json:"sha256"` }
type Manifest struct { Schema string `json:"schema"`; JobID string `json:"job_id"`; Generation uint64 `json:"generation"`; Complete bool `json:"complete"`; PolicyVersion string `json:"policy_version"`; PolicyDigest string `json:"policy_digest"`; CorpusDigest string `json:"corpus_digest"`; Files []FileDigest `json:"files"`; Digest string `json:"digest"` }

func confidence(value float64) string { if value>=0.9{return "HIGH"}; if value>=0.75{return "MEDIUM"}; return "LOW" }
func priority(category string, value float64) string { if (category=="US_SSN"||category=="PAYMENT_CARD")&&value>=0.9{return "P0"}; if value>=0.9{return "P1"}; if value>=0.75{return "P2"}; return "P3" }
func keyText(k SummaryKey) string { return k.Category+"\x1f"+k.Confidence+"\x1f"+k.SourceID+"\x1f"+k.Department+"\x1f"+k.Region+"\x1f"+k.Priority }

func Aggregate(job model.Job, shards []model.Shard, sources []model.Source, findings []model.Finding, scanErrors []model.ScanError, truncations []model.Truncation) (Report,error) {
	result:=Report{Schema:"enterprise-pii-report/v1",Tenant:job.Tenant,JobID:job.ID,Generation:job.Generation,PolicyVersion:job.PolicyVersion,PolicyDigest:job.PolicyDigest,CorpusDigest:job.CorpusDigest,Examples:[]model.Finding{}}
	for _,shard:=range shards{switch shard.State{case model.ShardCommitted:result.Completeness.Committed++;case model.ShardSkipped:result.Completeness.Skipped++;case model.ShardFailed:result.Completeness.Failed++;default:if shard.Required{result.Completeness.Missing++}}}
	result.Completeness.Errors=len(scanErrors); result.Completeness.Truncations=len(truncations); result.Completeness.Complete=result.Completeness.Missing==0
	if !result.Completeness.Complete{return result,errors.New("required shards are not terminal")}
	sourceMap:=map[string]model.Source{}; for _,source:=range sources{sourceMap[source.ID]=source}
	rows:=map[string]*SummaryRow{}; fingerprints:=map[string]map[string]bool{}
	for _,finding:=range findings{source:=sourceMap[finding.Location.SourceID]; key:=SummaryKey{Category:finding.Category,Confidence:confidence(finding.Confidence),SourceID:source.ID,Department:source.Department,Region:source.Region,Priority:priority(finding.Category,finding.Confidence)}; text:=keyText(key); if rows[text]==nil{rows[text]=&SummaryRow{Key:key};fingerprints[text]=map[string]bool{}}; if finding.Suppressed{rows[text].Suppressed++}else{rows[text].Findings++; if len(result.Examples)<20{result.Examples=append(result.Examples,finding)}}; fingerprints[text][finding.Fingerprint]=true}
	keys:=make([]string,0,len(rows)); for key:=range rows{keys=append(keys,key)}; sort.Strings(keys); for _,key:=range keys{rows[key].DistinctFingerprints=len(fingerprints[key]);result.Rows=append(result.Rows,*rows[key])}
	return result,nil
}

func JSON(value any) ([]byte,error) { return json.Marshal(value) }
func CSV(report Report) ([]byte,error) { var buffer bytes.Buffer; writer:=csv.NewWriter(&buffer); _=writer.Write([]string{"category","confidence","source_id","department","region","priority","findings","suppressed","distinct_fingerprints"}); for _,row:=range report.Rows{_ = writer.Write([]string{row.Key.Category,row.Key.Confidence,row.Key.SourceID,row.Key.Department,row.Key.Region,row.Key.Priority,strconv.Itoa(row.Findings),strconv.Itoa(row.Suppressed),strconv.Itoa(row.DistinctFingerprints)})}; writer.Flush(); return buffer.Bytes(),writer.Error() }
func digest(body []byte) string { sum:=sha256.Sum256(body); return hex.EncodeToString(sum[:]) }
func BuildManifest(report Report, jsonBody,csvBody []byte) (Manifest,error) { manifest:=Manifest{Schema:"enterprise-pii-manifest/v1",JobID:report.JobID,Generation:report.Generation,Complete:report.Completeness.Complete,PolicyVersion:report.PolicyVersion,PolicyDigest:report.PolicyDigest,CorpusDigest:report.CorpusDigest,Files:[]FileDigest{{Name:"report.json",Bytes:len(jsonBody),SHA256:digest(jsonBody)},{Name:"report.csv",Bytes:len(csvBody),SHA256:digest(csvBody)}}}; body,err:=json.Marshal(manifest); if err!=nil{return Manifest{},err}; manifest.Digest=digest(body); return manifest,nil }