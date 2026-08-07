package com.freight.selftest;

import com.freight.codec.Codec;
import com.freight.codec.CodecRegistry;
import com.freight.format.FormatRegistry;
import com.freight.format.Formatter;
import com.freight.hash.HashAlgorithm;
import com.freight.hash.HashRegistry;
import com.freight.json.JsonValue;
import com.freight.norm.Normalizer;
import com.freight.norm.NormalizerRegistry;
import com.freight.rules.ProbeRecord;
import com.freight.rules.RuleRegistry;
import com.freight.rules.TriageRule;
import com.freight.stats.StatKernel;
import com.freight.stats.StatRegistry;
import com.freight.tables.CarrierTable;
import com.freight.tables.CommodityTable;
import com.freight.tables.HazmatTable;
import com.freight.tables.LaneTable;
import com.freight.tables.TariffTable;
import com.freight.tables.ZoneTable;
import com.freight.util.Sha256Util;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Builds the cross language conformance report for the Java implementation. */
public final class SelftestReport {

    private static final long FNV_OFFSET = 0xCBF29CE484222325L;
    private static final long FNV_PRIME = 0x100000001B3L;

    private SelftestReport() {
    }

    private static long fold(long state, byte[] data) {
        long value = state;
        for (int i = 0; i < data.length; i++) {
            value ^= (data[i] & 0xFF);
            value *= FNV_PRIME;
        }
        return value;
    }

    private static long fold(long state, String text) {
        return fold(state, text.getBytes(StandardCharsets.UTF_8));
    }

    private static String hex64(long value) {
        return String.format(java.util.Locale.ROOT, "%016x", value);
    }

    public static JsonValue build() {
        Map<String, Map<String, String>> families = new TreeMap<String, Map<String, String>>();

        Map<String, String> hashes = new TreeMap<String, String>();
        for (HashAlgorithm algorithm : HashRegistry.all()) {
            long folded = FNV_OFFSET;
            for (int p = 0; p < Probes.PROBE_COUNT; p++) {
                byte[] probe = Probes.probeString(p).getBytes(StandardCharsets.UTF_8);
                folded = fold(folded, hex64(algorithm.apply(probe)));
            }
            hashes.put(algorithm.name(), hex64(folded));
        }
        families.put("hash", hashes);

        Map<String, String> codecs = new TreeMap<String, String>();
        for (Codec codec : CodecRegistry.all()) {
            long folded = FNV_OFFSET;
            boolean roundTrip = true;
            for (int p = 0; p < Probes.PROBE_COUNT; p++) {
                byte[] probe = Probes.probeString(p).getBytes(StandardCharsets.UTF_8);
                byte[] encoded = codec.encode(probe);
                folded = fold(folded, encoded);
                if (!Arrays.equals(codec.decode(encoded), probe)) {
                    roundTrip = false;
                }
            }
            if (!roundTrip) {
                folded ^= 0xDEADBEEFCAFEF00DL;
            }
            codecs.put(codec.name(), hex64(folded));
        }
        families.put("codec", codecs);

        Map<String, String> stats = new TreeMap<String, String>();
        for (StatKernel kernel : StatRegistry.all()) {
            long folded = FNV_OFFSET;
            for (int s = 0; s < Probes.SERIES_COUNT; s++) {
                folded = fold(folded, Long.toString(kernel.apply(Probes.probeSeries(s))));
            }
            stats.put(kernel.name(), hex64(folded));
        }
        families.put("stats", stats);

        Map<String, String> rules = new TreeMap<String, String>();
        List<ProbeRecord> records = Probes.probeRecords();
        for (TriageRule rule : RuleRegistry.all()) {
            long folded = FNV_OFFSET;
            for (ProbeRecord record : records) {
                folded = fold(folded, rule.apply(record) ? "1" : "0");
            }
            rules.put(rule.name(), hex64(folded));
        }
        families.put("rules", rules);

        Map<String, String> formats = new TreeMap<String, String>();
        for (Formatter formatter : FormatRegistry.all()) {
            long folded = FNV_OFFSET;
            for (int s = 0; s < Probes.SERIES_COUNT; s++) {
                for (long value : Probes.probeSeries(s)) {
                    folded = fold(folded, formatter.apply(value));
                    folded = fold(folded, formatter.apply(-value));
                }
            }
            formats.put(formatter.name(), hex64(folded));
        }
        families.put("format", formats);

        Map<String, String> norms = new TreeMap<String, String>();
        for (Normalizer normalizer : NormalizerRegistry.all()) {
            long folded = FNV_OFFSET;
            for (int p = 0; p < Probes.PROBE_COUNT; p++) {
                folded = fold(folded, normalizer.apply(Probes.probeString(p)));
            }
            norms.put(normalizer.name(), hex64(folded));
        }
        families.put("norm", norms);

        Map<String, String> tables = new TreeMap<String, String>();
        long folded = FNV_OFFSET;
        for (LaneTable.Row row : LaneTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("lane", hex64(folded));
        folded = FNV_OFFSET;
        for (CarrierTable.Row row : CarrierTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("carrier", hex64(folded));
        folded = FNV_OFFSET;
        for (CommodityTable.Row row : CommodityTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("commodity", hex64(folded));
        folded = FNV_OFFSET;
        for (TariffTable.Row row : TariffTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("tariff", hex64(folded));
        folded = FNV_OFFSET;
        for (ZoneTable.Row row : ZoneTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("zone", hex64(folded));
        folded = FNV_OFFSET;
        for (HazmatTable.Row row : HazmatTable.rows()) {
            folded = fold(folded, row.canonical());
        }
        tables.put("hazmat", hex64(folded));
        families.put("tables", tables);

        Sha256Util hasher = new Sha256Util();
        JsonValue familyJson = JsonValue.object();
        for (Map.Entry<String, Map<String, String>> family : families.entrySet()) {
            JsonValue bucket = JsonValue.object();
            for (Map.Entry<String, String> entry : family.getValue().entrySet()) {
                bucket.put(entry.getKey(), entry.getValue());
                hasher.update(family.getKey() + "|" + entry.getKey() + "|" + entry.getValue() + "\n");
            }
            familyJson.put(family.getKey(), bucket);
        }

        JsonValue report = JsonValue.object();
        report.put("digest", hasher.hex());
        report.put("families", familyJson);
        report.put("generator", "java");
        report.put("probe_count", (long) Probes.PROBE_COUNT);
        report.put("record_count", (long) Probes.RECORD_COUNT);
        report.put("schema_version", "freight-selftest/2");
        report.put("series_count", (long) Probes.SERIES_COUNT);
        return report;
    }
}
