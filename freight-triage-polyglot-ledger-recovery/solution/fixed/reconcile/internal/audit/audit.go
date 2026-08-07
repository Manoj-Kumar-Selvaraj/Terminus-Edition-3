// Package audit reconciles the native ledger snapshot against the intake journal.
package audit

import (
	"sort"

	"freight/reconcile/internal/model"
	"freight/reconcile/internal/timeutil"
)

// Row is one reconciled manifest.
type Row struct {
	ManifestID      string
	LaneID          string
	ArrivalEpochS   int64
	WindowIndex     int64
	SlotIndex       int64
	Status          string
	State           string
	GrossKg         int64
	NetHeldKg       int64
	AvailableKg     int64
	GrossTonnes     string
	SealDigest      string
	TariffBand      string
	TariffRateCents int64
	AccruedCents    int64
}

// OrphanHold is an intake hold with no matching ledger entry.
type OrphanHold struct {
	ManifestID string
	NetHeldKg  int64
	OpenHolds  int64
}

// LaneRollup aggregates reconciled rows for one lane.
type LaneRollup struct {
	LaneID         string
	EntryCount     int64
	AcceptedCount  int64
	AllocatedKg    int64
	HeldKg         int64
	AvailableKg    int64
	AccruedCents   int64
	SlotsUsed      int64
	SlotCount      int64
	SlotCapacityKg int64
}

// WindowRollup aggregates reconciled rows for one dock window.
type WindowRollup struct {
	WindowIndex        int64
	WindowStartEpochS  int64
	WindowEndEpochS    int64
	EntryCount         int64
	AcceptedCount      int64
	GrossKg            int64
	HeldKg             int64
}

// Result is the full reconciliation outcome.
type Result struct {
	Rows                 []Row
	Orphans              []OrphanHold
	LaneRollups          []LaneRollup
	WindowRollups        []WindowRollup
	StateCounts          map[string]int64
	SealDigestMismatches int64
}

// AccruedCents bills the available tonnage at the manifest tariff rate,
// rounding half up.
func AccruedCents(rateCents, billableKg int64) int64 {
	return (rateCents*billableKg + 500) / 1000
}

// Window membership is half open: start <= arrival < end.
func inWindow(arrivalEpochS, start, end int64) bool {
	return arrivalEpochS >= start && arrivalEpochS < end
}

func slotsUsed(indices map[int64]bool) int64 {
	used := int64(0)
	for index := range indices {
		if index > 0 {
			used++
		}
	}
	return used
}

func classify(status string, grossKg, netHeldKg int64) string {
	if status != "accepted" {
		if netHeldKg > 0 {
			return "unreconciled"
		}
		return "excluded"
	}
	if netHeldKg == 0 {
		return "clear"
	}
	if netHeldKg > grossKg {
		return "over_held"
	}
	return "held"
}

// Reconcile joins ledger entries to intake holds and produces audit rows.
func Reconcile(snapshot *model.Snapshot, journal *model.Journal,
	lanes map[string]model.LaneRecord) *Result {

	holds := make(map[string]model.JournalHold, len(journal.Holds))
	for _, hold := range journal.Holds {
		holds[hold.ManifestID] = hold
	}

	result := &Result{
		StateCounts: map[string]int64{
			"clear":        0,
			"excluded":     0,
			"held":         0,
			"over_held":    0,
			"unreconciled": 0,
		},
	}

	seen := make(map[string]bool, len(snapshot.Entries))
	rows := make([]Row, 0, len(snapshot.Entries))
	for _, entry := range snapshot.Entries {
		seen[entry.ManifestID] = true
		hold, hasHold := holds[entry.ManifestID]
		netHeld := int64(0)
		if hasHold {
			netHeld = hold.NetHeldKg
			if hold.SealDigest != entry.SealDigest {
				result.SealDigestMismatches++
			}
		}
		state := classify(entry.Status, entry.GrossKg, netHeld)
		available := int64(0)
		if entry.Status == "accepted" {
			available = entry.GrossKg - netHeld
			if available < 0 {
				available = 0
			}
		}
		rows = append(rows, Row{
			ManifestID:      entry.ManifestID,
			LaneID:          entry.LaneID,
			ArrivalEpochS:   entry.ArrivalEpochS,
			WindowIndex:     entry.WindowIndex,
			SlotIndex:       entry.SlotIndex,
			Status:          entry.Status,
			State:           state,
			GrossKg:         entry.GrossKg,
			NetHeldKg:       netHeld,
			AvailableKg:     available,
			GrossTonnes:     timeutil.FormatTonnes(entry.GrossKg),
			SealDigest:      entry.SealDigest,
			TariffBand:      entry.TariffBand,
			TariffRateCents: entry.TariffRateCents,
			AccruedCents:    AccruedCents(entry.TariffRateCents, available),
		})
		result.StateCounts[state]++
	}

	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].LaneID != rows[j].LaneID {
			return rows[i].LaneID < rows[j].LaneID
		}
		if rows[i].WindowIndex != rows[j].WindowIndex {
			return rows[i].WindowIndex < rows[j].WindowIndex
		}
		if rows[i].SlotIndex != rows[j].SlotIndex {
			return rows[i].SlotIndex < rows[j].SlotIndex
		}
		return rows[i].ManifestID < rows[j].ManifestID
	})
	result.Rows = rows

	orphans := make([]OrphanHold, 0)
	for _, hold := range journal.Holds {
		if seen[hold.ManifestID] {
			continue
		}
		orphans = append(orphans, OrphanHold{
			ManifestID: hold.ManifestID,
			NetHeldKg:  hold.NetHeldKg,
			OpenHolds:  hold.OpenHolds,
		})
	}
	sort.SliceStable(orphans, func(i, j int) bool {
		return orphans[i].ManifestID < orphans[j].ManifestID
	})
	result.Orphans = orphans

	laneIndex := make(map[string]*LaneRollup)
	laneSlots := make(map[string]map[int64]bool)
	laneOrder := make([]string, 0)
	for _, row := range rows {
		lane, registered := lanes[row.LaneID]
		if !registered {
			// Lane rollups publish registry geometry, so an unregistered lane
			// has no rollup of its own.
			continue
		}
		rollup, ok := laneIndex[row.LaneID]
		if !ok {
			rollup = &LaneRollup{
				LaneID:         row.LaneID,
				SlotCount:      lane.SlotCount,
				SlotCapacityKg: lane.SlotCapacityKg,
			}
			laneIndex[row.LaneID] = rollup
			laneSlots[row.LaneID] = make(map[int64]bool)
			laneOrder = append(laneOrder, row.LaneID)
		}
		rollup.EntryCount++
		rollup.HeldKg += row.NetHeldKg
		rollup.AvailableKg += row.AvailableKg
		rollup.AccruedCents += row.AccruedCents
		if row.Status == "accepted" {
			rollup.AcceptedCount++
			laneSlots[row.LaneID][row.SlotIndex] = true
			rollup.AllocatedKg += row.GrossKg
		}
	}
	sort.Strings(laneOrder)
	for _, laneID := range laneOrder {
		rollup := laneIndex[laneID]
		rollup.SlotsUsed = slotsUsed(laneSlots[laneID])
		result.LaneRollups = append(result.LaneRollups, *rollup)
	}

	windowSet := make(map[int64]bool)
	for _, row := range rows {
		windowSet[row.WindowIndex] = true
	}
	windows := make([]int64, 0, len(windowSet))
	for window := range windowSet {
		windows = append(windows, window)
	}
	sort.Slice(windows, func(i, j int) bool { return windows[i] < windows[j] })
	for _, window := range windows {
		start := timeutil.WindowStart(window)
		end := timeutil.WindowEnd(window)
		rollup := WindowRollup{
			WindowIndex:       window,
			WindowStartEpochS: start,
			WindowEndEpochS:   end,
		}
		for _, row := range rows {
			if !inWindow(row.ArrivalEpochS, start, end) {
				continue
			}
			rollup.EntryCount++
			rollup.GrossKg += row.GrossKg
			rollup.HeldKg += row.NetHeldKg
			if row.Status == "accepted" {
				rollup.AcceptedCount++
			}
		}
		result.WindowRollups = append(result.WindowRollups, rollup)
	}

	return result
}
