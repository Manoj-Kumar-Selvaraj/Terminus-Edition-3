// Package report renders reconciliation artifacts.
package report

import (
	"bytes"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"

	"freight/reconcile/internal/audit"
	"freight/reconcile/internal/model"
	"freight/reconcile/internal/timeutil"
)

// RenderCSV serializes reconciled rows into the contracted audit ledger.
func RenderCSV(rows []audit.Row) ([]byte, error) {
	buffer := &bytes.Buffer{}
	writer := csv.NewWriter(buffer)
	writer.UseCRLF = true

	header := []string{
		"manifest_id", "lane_id", "window_index", "slot_index", "state", "status",
		"gross_kg", "net_held_kg", "available_kg", "gross_tonnes", "seal_digest",
		"tariff_band", "tariff_rate_cents", "accrued_cents",
	}
	if err := writer.Write(header); err != nil {
		return nil, err
	}
	for _, row := range rows {
		record := []string{
			row.ManifestID,
			row.LaneID,
			strconv.FormatInt(row.WindowIndex, 10),
			strconv.FormatInt(row.SlotIndex, 10),
			row.State,
			row.Status,
			strconv.FormatInt(row.GrossKg, 10),
			strconv.FormatInt(row.NetHeldKg, 10),
			strconv.FormatInt(row.AvailableKg, 10),
			row.GrossTonnes,
			row.SealDigest,
			row.TariffBand,
			strconv.FormatInt(row.TariffRateCents, 10),
			strconv.FormatInt(row.AccruedCents, 10),
		}
		if err := writer.Write(record); err != nil {
			return nil, err
		}
	}
	writer.Flush()
	if err := writer.Error(); err != nil {
		return nil, err
	}
	return buffer.Bytes(), nil
}

// CanonicalRow renders one audit digest line.
func CanonicalRow(row audit.Row) string {
	return fmt.Sprintf("%s|%s|%d|%d|%s|%d|%d|%d|%d\n",
		row.ManifestID, row.LaneID, row.WindowIndex, row.SlotIndex, row.State,
		row.GrossKg, row.NetHeldKg, row.AvailableKg, row.AccruedCents)
}

// Digest hashes a byte slice with SHA-256.
func Digest(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// RecomputeLedgerDigest rebuilds the native ledger digest from snapshot entries.
func RecomputeLedgerDigest(snapshot *model.Snapshot) string {
	hasher := sha256.New()
	for _, entry := range snapshot.Entries {
		hasher.Write([]byte(entry.Canonical()))
	}
	return hex.EncodeToString(hasher.Sum(nil))
}

// RecomputeJournalDigest rebuilds the intake journal digest from its events.
func RecomputeJournalDigest(journal *model.Journal) string {
	hasher := sha256.New()
	for _, event := range journal.Events {
		hasher.Write([]byte(event.Canonical()))
	}
	return hex.EncodeToString(hasher.Sum(nil))
}

// Build assembles the audit report document.
func Build(snapshot *model.Snapshot, journal *model.Journal, result *audit.Result,
	csvBytes []byte) map[string]any {

	laneRollups := make([]map[string]any, 0, len(result.LaneRollups))
	for _, lane := range result.LaneRollups {
		laneRollups = append(laneRollups, map[string]any{
			"accepted_count":   lane.AcceptedCount,
			"accrued_cents":    lane.AccruedCents,
			"allocated_kg":     lane.AllocatedKg,
			"allocated_tonnes": timeutil.FormatTonnes(lane.AllocatedKg),
			"available_kg":     lane.AvailableKg,
			"entry_count":      lane.EntryCount,
			"held_kg":          lane.HeldKg,
			"lane_id":          lane.LaneID,
			"slot_capacity_kg": lane.SlotCapacityKg,
			"slot_count":       lane.SlotCount,
			"slots_used":       lane.SlotsUsed,
		})
	}

	windowRollups := make([]map[string]any, 0, len(result.WindowRollups))
	for _, window := range result.WindowRollups {
		windowRollups = append(windowRollups, map[string]any{
			"accepted_count":       window.AcceptedCount,
			"entry_count":          window.EntryCount,
			"gross_kg":             window.GrossKg,
			"held_kg":              window.HeldKg,
			"window_end_epoch_s":   window.WindowEndEpochS,
			"window_index":         window.WindowIndex,
			"window_start_epoch_s": window.WindowStartEpochS,
		})
	}

	orphans := make([]map[string]any, 0, len(result.Orphans))
	totalOrphanKg := int64(0)
	for _, orphan := range result.Orphans {
		orphans = append(orphans, map[string]any{
			"manifest_id": orphan.ManifestID,
			"net_held_kg": orphan.NetHeldKg,
			"open_holds":  orphan.OpenHolds,
		})
		totalOrphanKg += orphan.NetHeldKg
	}

	accepted := int64(0)
	heldKg := int64(0)
	availableKg := int64(0)
	accruedCents := int64(0)
	canonical := &bytes.Buffer{}
	for _, row := range result.Rows {
		if row.Status == "accepted" {
			accepted++
		}
		heldKg += row.NetHeldKg
		availableKg += row.AvailableKg
		accruedCents += row.AccruedCents
		canonical.WriteString(CanonicalRow(row))
	}

	recomputedLedger := RecomputeLedgerDigest(snapshot)
	recomputedJournal := RecomputeJournalDigest(journal)

	stateCounts := map[string]any{}
	for name, count := range result.StateCounts {
		stateCounts[name] = count
	}

	return map[string]any{
		"csv_digest": Digest(csvBytes),
		"digests_match": map[string]any{
			"journal": recomputedJournal == journal.JournalDigest,
			"ledger":  recomputedLedger == snapshot.LedgerDigest,
		},
		"epoch_base_s":               timeutil.EpochBaseSeconds,
		"generator":                  "freight-reconcile",
		"journal_digest":             journal.JournalDigest,
		"lane_rollups":               laneRollups,
		"ledger_digest":              snapshot.LedgerDigest,
		"orphan_holds":               orphans,
		"recomputed_journal_digest":  recomputedJournal,
		"recomputed_ledger_digest":   recomputedLedger,
		"report_digest":              Digest(canonical.Bytes()),
		"schema_version":             "freight-audit/2",
		"seal_digest_mismatches":     result.SealDigestMismatches,
		"state_counts":               stateCounts,
		"totals": map[string]any{
			"accepted":          accepted,
			"accrued_cents":     accruedCents,
			"available_kg":      availableKg,
			"held_kg":           heldKg,
			"manifests":         int64(len(result.Rows)),
			"orphan_hold_count": int64(len(result.Orphans)),
			"orphan_held_kg":    totalOrphanKg,
		},
		"window_rollups": windowRollups,
	}
}

// WriteFile writes bytes to a path, creating parent directories as needed.
func WriteFile(path string, data []byte) error {
	if parent := filepath.Dir(path); parent != "" {
		if err := os.MkdirAll(parent, 0o755); err != nil {
			return err
		}
	}
	return os.WriteFile(path, data, 0o644)
}

// WriteJSON writes a document with two space indentation and a trailing newline.
func WriteJSON(path string, document any) error {
	encoded, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		return err
	}
	encoded = append(encoded, '\n')
	return WriteFile(path, encoded)
}

// FormatInt is a small helper used by the CLI summary output.
func FormatInt(value int64) string {
	return strconv.FormatInt(value, 10)
}
