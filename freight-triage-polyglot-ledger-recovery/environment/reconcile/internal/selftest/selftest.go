// Package selftest builds the cross language conformance report.
package selftest

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"

	"freight/reconcile/internal/codecx"
	"freight/reconcile/internal/formatx"
	"freight/reconcile/internal/hashx"
	"freight/reconcile/internal/normx"
	"freight/reconcile/internal/rulex"
	"freight/reconcile/internal/statx"
	"freight/reconcile/internal/tablex"
)

const (
	probeCount   = 64
	seriesCount  = 24
	seriesLength = 17
	recordCount  = 40
)

const fnvOffset uint64 = 14695981039346656037
const fnvPrime uint64 = 1099511628211

func fold(state uint64, data []byte) uint64 {
	value := state
	for _, b := range data {
		value ^= uint64(b)
		value *= fnvPrime
	}
	return value
}

func foldString(state uint64, text string) uint64 {
	return fold(state, []byte(text))
}

func hex64(value uint64) string {
	return fmt.Sprintf("%016x", value)
}

// Mix32 is the shared deterministic probe mixer.
func Mix32(seed uint32) uint32 {
	x := seed
	x ^= x >> 16
	x *= 0x7FEB352D
	x ^= x >> 15
	x *= 0x846CA68B
	x ^= x >> 16
	return x
}

// ProbeString builds probe number index.
func ProbeString(index int) string {
	buffer := &bytes.Buffer{}
	fmt.Fprintf(buffer, "FRT-%04d-", index)
	for k := 0; k < index%11; k++ {
		buffer.WriteByte(byte('a' + ((index*7 + k*3) % 26)))
	}
	return buffer.String()
}

// ProbeSeries builds integer series number series.
func ProbeSeries(series int) []int64 {
	values := make([]int64, 0, seriesLength)
	for k := 0; k < seriesLength; k++ {
		m := Mix32(uint32(series*977 + k*31))
		values = append(values, 3+int64(m%4093))
	}
	return values
}

// ProbeRecords builds the triage record corpus.
func ProbeRecords() []rulex.Record {
	records := make([]rulex.Record, 0, recordCount)
	for index := 0; index < recordCount; index++ {
		m := Mix32(uint32(index*131 + 17))
		records = append(records, rulex.Record{
			RecordID:    fmt.Sprintf("RC-%03d", index),
			LaneIndex:   int64(m % 360),
			MassKg:      50 + int64((m>>7)%48000),
			Priority:    int64((m >> 3) % 5),
			HazmatClass: int64((m >> 11) % 9),
			SealLength:  6 + int64((m>>17)%7),
		})
	}
	return records
}

// Build assembles the Go conformance report.
func Build() map[string]any {
	families := map[string]map[string]string{}

	hashes := map[string]string{}
	for _, algorithm := range hashx.Registry() {
		folded := fnvOffset
		for p := 0; p < probeCount; p++ {
			folded = foldString(folded, hex64(algorithm.Apply([]byte(ProbeString(p)))))
		}
		hashes[algorithm.Name] = hex64(folded)
	}
	families["hash"] = hashes

	codecs := map[string]string{}
	for _, codec := range codecx.Registry() {
		folded := fnvOffset
		roundTrip := true
		for p := 0; p < probeCount; p++ {
			probe := []byte(ProbeString(p))
			encoded := codec.Encode(probe)
			folded = fold(folded, encoded)
			if !bytes.Equal(codec.Decode(encoded), probe) {
				roundTrip = false
			}
		}
		if !roundTrip {
			folded ^= 0xDEADBEEFCAFEF00D
		}
		codecs[codec.Name] = hex64(folded)
	}
	families["codec"] = codecs

	stats := map[string]string{}
	for _, kernel := range statx.Registry() {
		folded := fnvOffset
		for s := 0; s < seriesCount; s++ {
			folded = foldString(folded, fmt.Sprintf("%d", kernel.Apply(ProbeSeries(s))))
		}
		stats[kernel.Name] = hex64(folded)
	}
	families["stats"] = stats

	rules := map[string]string{}
	records := ProbeRecords()
	for _, rule := range rulex.Registry() {
		folded := fnvOffset
		for _, record := range records {
			if rule.Apply(record) {
				folded = foldString(folded, "1")
			} else {
				folded = foldString(folded, "0")
			}
		}
		rules[rule.Name] = hex64(folded)
	}
	families["rules"] = rules

	formats := map[string]string{}
	for _, formatter := range formatx.Registry() {
		folded := fnvOffset
		for s := 0; s < seriesCount; s++ {
			for _, value := range ProbeSeries(s) {
				folded = foldString(folded, formatter.Apply(value))
				folded = foldString(folded, formatter.Apply(-value))
			}
		}
		formats[formatter.Name] = hex64(folded)
	}
	families["format"] = formats

	norms := map[string]string{}
	for _, normalizer := range normx.Registry() {
		folded := fnvOffset
		for p := 0; p < probeCount; p++ {
			folded = foldString(folded, normalizer.Apply(ProbeString(p)))
		}
		norms[normalizer.Name] = hex64(folded)
	}
	families["norm"] = norms

	tables := map[string]string{}
	folded := fnvOffset
	for _, row := range tablex.LaneRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["lane"] = hex64(folded)
	folded = fnvOffset
	for _, row := range tablex.CarrierRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["carrier"] = hex64(folded)
	folded = fnvOffset
	for _, row := range tablex.CommodityRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["commodity"] = hex64(folded)
	folded = fnvOffset
	for _, row := range tablex.TariffRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["tariff"] = hex64(folded)
	folded = fnvOffset
	for _, row := range tablex.ZoneRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["zone"] = hex64(folded)
	folded = fnvOffset
	for _, row := range tablex.HazmatRows() {
		folded = foldString(folded, row.Canonical())
	}
	tables["hazmat"] = hex64(folded)
	families["tables"] = tables

	familyNames := make([]string, 0, len(families))
	for name := range families {
		familyNames = append(familyNames, name)
	}
	sort.Strings(familyNames)

	hasher := sha256.New()
	document := map[string]any{}
	for _, familyName := range familyNames {
		entries := families[familyName]
		names := make([]string, 0, len(entries))
		for name := range entries {
			names = append(names, name)
		}
		sort.Strings(names)
		bucket := map[string]any{}
		for _, name := range names {
			bucket[name] = entries[name]
			hasher.Write([]byte(familyName + "|" + name + "|" + entries[name] + "\n"))
		}
		document[familyName] = bucket
	}

	return map[string]any{
		"digest":         hex.EncodeToString(hasher.Sum(nil)),
		"families":       document,
		"generator":      "go",
		"probe_count":    probeCount,
		"record_count":   recordCount,
		"schema_version": "freight-selftest/2",
		"series_count":   seriesCount,
	}
}
