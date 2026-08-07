// Package model mirrors the on-disk freight ledger and intake documents.
package model

import (
	"encoding/json"
	"fmt"
	"os"
)

// LedgerEntry is one manifest row from the native ledger snapshot.
type LedgerEntry struct {
	ArrivalEpochS   int64  `json:"arrival_epoch_s"`
	AveragePieceG   int64  `json:"average_piece_g"`
	CarrierCode     string `json:"carrier_code"`
	CommodityCode   string `json:"commodity_code"`
	GrossKg         int64  `json:"gross_kg"`
	GrossTonnes     string `json:"gross_tonnes"`
	HazmatMax       int64  `json:"hazmat_max"`
	LaneID          string `json:"lane_id"`
	ManifestID      string `json:"manifest_id"`
	PieceCount      int64  `json:"piece_count"`
	Priority        int64  `json:"priority"`
	Seal            string `json:"seal"`
	SealDigest      string `json:"seal_digest"`
	SlotIndex       int64  `json:"slot_index"`
	Status          string `json:"status"`
	TariffBand      string `json:"tariff_band"`
	TariffRateCents int64  `json:"tariff_rate_cents"`
	WindowIndex     int64  `json:"window_index"`
}

// Canonical renders the digest line for one ledger entry.
func (entry LedgerEntry) Canonical() string {
	return fmt.Sprintf("%s|%s|%d|%d|%d|%d|%s|%s|%s|%d\n",
		entry.ManifestID, entry.LaneID, entry.WindowIndex, entry.SlotIndex,
		entry.ArrivalEpochS, entry.GrossKg, entry.Status, entry.SealDigest,
		entry.TariffBand, entry.TariffRateCents)
}

// LaneTotal is the per-lane rollup published by the native engine.
type LaneTotal struct {
	AcceptedCount      int64  `json:"accepted_count"`
	AllocatedKg        int64  `json:"allocated_kg"`
	AllocatedTonnes    string `json:"allocated_tonnes"`
	DuplicateSealCount int64  `json:"duplicate_seal_count"`
	EntryCount         int64  `json:"entry_count"`
	InvalidCount       int64  `json:"invalid_count"`
	LaneID             string `json:"lane_id"`
	OverflowCount      int64  `json:"overflow_count"`
	SlotsUsed          int64  `json:"slots_used"`
}

// Snapshot is the whole native ledger document.
type Snapshot struct {
	Entries       []LedgerEntry  `json:"entries"`
	EpochBaseS    int64          `json:"epoch_base_s"`
	Generator     string         `json:"generator"`
	LaneTotals    []LaneTotal    `json:"lane_totals"`
	LedgerDigest  string         `json:"ledger_digest"`
	SchemaVersion string         `json:"schema_version"`
	Totals        map[string]any `json:"totals"`
	WindowSeconds int64          `json:"window_seconds"`
}

// JournalEvent is one applied or rejected intake request.
type JournalEvent struct {
	Accepted   bool   `json:"accepted"`
	AtEpochS   int64  `json:"at_epoch_s"`
	Code       string `json:"code"`
	Kind       string `json:"kind"`
	ManifestID string `json:"manifest_id"`
	Ref        int64  `json:"ref"`
	Seq        int64  `json:"seq"`
	TonnesKg   int64  `json:"tonnes_kg"`
}

// Canonical renders the digest line for one journal event.
func (event JournalEvent) Canonical() string {
	accepted := "0"
	if event.Accepted {
		accepted = "1"
	}
	return fmt.Sprintf("%d|%s|%s|%d|%s|%s|%d|%d\n",
		event.Seq, event.Kind, event.ManifestID, event.AtEpochS, accepted,
		event.Code, event.Ref, event.TonnesKg)
}

// JournalHold is the per-manifest hold aggregate published by intake.
type JournalHold struct {
	FirstHoldEpochS int64  `json:"first_hold_epoch_s"`
	HeldKg          int64  `json:"held_kg"`
	HeldTonnes      string `json:"held_tonnes"`
	LastEventEpochS int64  `json:"last_event_epoch_s"`
	ManifestID      string `json:"manifest_ref"`
	NetHeldKg       int64  `json:"net_held_kg"`
	NetHeldTonnes   string `json:"net_held_tonnes"`
	OpenHolds       int64  `json:"open_holds"`
	ReleasedKg      int64  `json:"released_kg"`
	Seal            string `json:"seal"`
	SealDigest      string `json:"seal_digest"`
}

// Journal is the whole intake journal document.
type Journal struct {
	EpochBaseS    int64          `json:"epoch_base_s"`
	Events        []JournalEvent `json:"events"`
	Generator     string         `json:"generator"`
	Holds         []JournalHold  `json:"holds"`
	JournalDigest string         `json:"journal_digest"`
	SchemaVersion string         `json:"schema_version"`
	Totals        map[string]any `json:"totals"`
	WindowSeconds int64          `json:"window_seconds"`
}

// LaneRecord is one row of the normative lane registry.
type LaneRecord struct {
	CrossDock      bool   `json:"cross_dock"`
	DestHub        string `json:"dest_hub"`
	LaneID         string `json:"lane_id"`
	OriginHub      string `json:"origin_hub"`
	ServiceClass   string `json:"service_class"`
	SlotCapacityKg int64  `json:"slot_capacity_kg"`
	SlotCount      int64  `json:"slot_count"`
	TransitMinutes int64  `json:"transit_minutes"`
}

// LaneRegistry is the lane registry document.
type LaneRegistry struct {
	Lanes         []LaneRecord `json:"lanes"`
	SchemaVersion string       `json:"schema_version"`
}

// LoadSnapshot reads a native ledger snapshot from disk.
func LoadSnapshot(path string) (*Snapshot, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read snapshot %s: %w", path, err)
	}
	snapshot := &Snapshot{}
	if err := json.Unmarshal(raw, snapshot); err != nil {
		return nil, fmt.Errorf("parse snapshot %s: %w", path, err)
	}
	return snapshot, nil
}

// LoadJournal reads an intake journal from disk.
func LoadJournal(path string) (*Journal, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read journal %s: %w", path, err)
	}
	journal := &Journal{}
	if err := json.Unmarshal(raw, journal); err != nil {
		return nil, fmt.Errorf("parse journal %s: %w", path, err)
	}
	return journal, nil
}

// LoadLaneRegistry reads the normative lane registry.
func LoadLaneRegistry(path string) (map[string]LaneRecord, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read lane registry %s: %w", path, err)
	}
	registry := &LaneRegistry{}
	if err := json.Unmarshal(raw, registry); err != nil {
		return nil, fmt.Errorf("parse lane registry %s: %w", path, err)
	}
	out := make(map[string]LaneRecord, len(registry.Lanes))
	for _, lane := range registry.Lanes {
		out[lane.LaneID] = lane
	}
	return out, nil
}
