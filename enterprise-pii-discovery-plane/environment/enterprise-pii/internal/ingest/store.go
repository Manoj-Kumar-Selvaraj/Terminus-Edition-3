package ingest

import (
	"errors"
	"sort"
	"strings"
	"sync"

	"enterprise-pii/internal/model"
)

type BatchReceipt struct { BatchID string `json:"batch_id"`; Digest string `json:"digest"`; Sequence uint64 `json:"sequence"`; FindingIDs []string `json:"finding_ids"` }
type Store struct { mu sync.RWMutex; receipts map[string]BatchReceipt; findings map[string]model.Finding; errors []model.ScanError; truncations []model.Truncation }
func New() *Store { return &Store{receipts:map[string]BatchReceipt{}, findings:map[string]model.Finding{}} }

func locationKey(f model.Finding) string {
	parts := []string{f.Location.SourceID, f.Location.CanonicalPath, f.Location.ArchiveMember, f.Location.RecordID, f.Location.FieldPath, string(rune(f.Location.ByteStart)), string(rune(f.Location.ByteEnd)), f.Category, f.Fingerprint}
	return strings.Join(parts, "\x1f")
}

func (s *Store) Accept(batch model.ResultBatch) (BatchReceipt, bool, error) {
	s.mu.Lock(); defer s.mu.Unlock()
	if batch.ID == "" || batch.BodyDigest == "" { return BatchReceipt{}, false, errors.New("batch identity missing") }
	if prior, ok := s.receipts[batch.ID]; ok {
		if prior.Digest != batch.BodyDigest { return BatchReceipt{}, false, errors.New("batch identity conflict") }
		return prior, true, nil
	}
	receipt := BatchReceipt{BatchID:batch.ID,Digest:batch.BodyDigest,Sequence:batch.Sequence}
	for _, finding := range batch.Findings {
		if finding.MaskedEvidence == "" || finding.Fingerprint == "" { return BatchReceipt{}, false, errors.New("privacy-safe evidence required") }
		key := locationKey(finding)
		if prior, ok := s.findings[key]; ok { prior.Lineage = merge(prior.Lineage, append(finding.Lineage, batch.ID)); s.findings[key]=prior; receipt.FindingIDs=append(receipt.FindingIDs,prior.ID); continue }
		finding.Lineage = merge(finding.Lineage, []string{batch.ID})
		s.findings[key]=finding
		receipt.FindingIDs=append(receipt.FindingIDs,finding.ID)
	}
	s.errors=append(s.errors,batch.Errors...)
	s.truncations=append(s.truncations,batch.Truncations...)
	s.receipts[batch.ID]=receipt
	return receipt,false,nil
}

func merge(left,right []string) []string { seen:=map[string]bool{}; for _,v:=range append(append([]string{},left...),right...){seen[v]=true}; out:=make([]string,0,len(seen)); for v:=range seen{out=append(out,v)}; sort.Strings(out); return out }
func (s *Store) Findings() []model.Finding { s.mu.RLock(); defer s.mu.RUnlock(); out:=make([]model.Finding,0,len(s.findings)); for _,v:=range s.findings{out=append(out,v)}; sort.Slice(out,func(i,j int)bool{return locationKey(out[i])<locationKey(out[j])}); return out }
func (s *Store) Errors() []model.ScanError { s.mu.RLock(); defer s.mu.RUnlock(); return append([]model.ScanError(nil),s.errors...) }
func (s *Store) Truncations() []model.Truncation { s.mu.RLock(); defer s.mu.RUnlock(); return append([]model.Truncation(nil),s.truncations...) }
func (s *Store) Receipts() []BatchReceipt { s.mu.RLock(); defer s.mu.RUnlock(); out:=make([]BatchReceipt,0,len(s.receipts)); for _,v:=range s.receipts{out=append(out,v)}; sort.Slice(out,func(i,j int)bool{return out[i].BatchID<out[j].BatchID}); return out }
