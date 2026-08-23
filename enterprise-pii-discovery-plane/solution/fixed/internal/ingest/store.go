package ingest

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"

	"enterprise-pii/internal/model"
)

type BatchReceipt struct {
	BatchID    string   `json:"batch_id"`
	Digest     string   `json:"digest"`
	Sequence   uint64   `json:"sequence"`
	FindingIDs []string `json:"finding_ids"`
}

type Store struct {
	mu          sync.RWMutex
	receipts    map[string]BatchReceipt
	findings    map[string]model.Finding
	errors      []model.ScanError
	truncations []model.Truncation
}

func New() *Store {
	return &Store{receipts: map[string]BatchReceipt{}, findings: map[string]model.Finding{}}
}

func locationKey(f model.Finding) string {
	parts := []string{
		f.Location.SourceID,
		f.Location.CanonicalPath,
		f.Location.ArchiveMember,
		f.Location.RecordID,
		f.Location.FieldPath,
		fmt.Sprintf("%d", f.Location.ByteStart),
		fmt.Sprintf("%d", f.Location.ByteEnd),
		f.Category,
		f.Fingerprint,
	}
	return strings.Join(parts, "\x1f")
}

func (s *Store) Accept(batch model.ResultBatch) (BatchReceipt, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if batch.ID == "" || batch.BodyDigest == "" {
		return BatchReceipt{}, false, errors.New("batch identity missing")
	}
	if prior, ok := s.receipts[batch.ID]; ok {
		if prior.Digest != batch.BodyDigest {
			return BatchReceipt{}, false, errors.New("batch identity conflict")
		}
		return prior, true, nil
	}
	receipt := BatchReceipt{BatchID: batch.ID, Digest: batch.BodyDigest, Sequence: batch.Sequence}
	for _, finding := range batch.Findings {
		if finding.MaskedEvidence == "" || finding.Fingerprint == "" {
			return BatchReceipt{}, false, errors.New("privacy-safe evidence required")
		}
		key := locationKey(finding)
		if prior, ok := s.findings[key]; ok {
			prior.Lineage = merge(prior.Lineage, append(finding.Lineage, batch.ID))
			s.findings[key] = prior
			receipt.FindingIDs = append(receipt.FindingIDs, prior.ID)
			continue
		}
		finding.Lineage = merge(finding.Lineage, []string{batch.ID})
		s.findings[key] = finding
		receipt.FindingIDs = append(receipt.FindingIDs, finding.ID)
	}
	s.errors = append(s.errors, batch.Errors...)
	s.truncations = append(s.truncations, batch.Truncations...)
	s.receipts[batch.ID] = receipt
	return receipt, false, nil
}

func merge(left, right []string) []string {
	seen := map[string]bool{}
	for _, value := range append(append([]string{}, left...), right...) {
		seen[value] = true
	}
	out := make([]string, 0, len(seen))
	for value := range seen {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func (s *Store) Restore(receipts []BatchReceipt, findings []model.Finding, errors []model.ScanError, truncations []model.Truncation) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.receipts = map[string]BatchReceipt{}
	s.findings = map[string]model.Finding{}
	for _, receipt := range receipts {
		s.receipts[receipt.BatchID] = receipt
	}
	for _, finding := range findings {
		s.findings[locationKey(finding)] = finding
	}
	s.errors = append([]model.ScanError(nil), errors...)
	s.truncations = append([]model.Truncation(nil), truncations...)
}

func (s *Store) Export() ([]BatchReceipt, []model.Finding, []model.ScanError, []model.Truncation) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	receipts := make([]BatchReceipt, 0, len(s.receipts))
	for _, receipt := range s.receipts {
		receipts = append(receipts, receipt)
	}
	sort.Slice(receipts, func(i, j int) bool { return receipts[i].BatchID < receipts[j].BatchID })
	findings := make([]model.Finding, 0, len(s.findings))
	for _, finding := range s.findings {
		findings = append(findings, finding)
	}
	sort.Slice(findings, func(i, j int) bool { return findings[i].ID < findings[j].ID })
	return receipts, findings, append([]model.ScanError(nil), s.errors...), append([]model.Truncation(nil), s.truncations...)
}

func (s *Store) Findings() []model.Finding {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]model.Finding, 0, len(s.findings))
	for _, value := range s.findings {
		out = append(out, value)
	}
	sort.Slice(out, func(i, j int) bool { return locationKey(out[i]) < locationKey(out[j]) })
	return out
}

func (s *Store) Errors() []model.ScanError {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return append([]model.ScanError(nil), s.errors...)
}

func (s *Store) Truncations() []model.Truncation {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return append([]model.Truncation(nil), s.truncations...)
}

func (s *Store) Receipts() []BatchReceipt {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]BatchReceipt, 0, len(s.receipts))
	for _, value := range s.receipts {
		out = append(out, value)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].BatchID < out[j].BatchID })
	return out
}
