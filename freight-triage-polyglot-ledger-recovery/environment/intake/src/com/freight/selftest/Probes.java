package com.freight.selftest;

import com.freight.rules.ProbeRecord;

import java.util.ArrayList;
import java.util.List;

/** Deterministic probe corpus shared by the C++, Java and Go selftests. */
public final class Probes {

    public static final int PROBE_COUNT = 64;
    public static final int SERIES_COUNT = 24;
    public static final int SERIES_LENGTH = 17;
    public static final int RECORD_COUNT = 40;

    private Probes() {
    }

    public static int mix32(int seed) {
        int x = seed;
        x ^= x >>> 16;
        x *= 0x7FEB352D;
        x ^= x >>> 15;
        x *= 0x846CA68B;
        x ^= x >>> 16;
        return x;
    }

    public static String probeString(int index) {
        StringBuilder out = new StringBuilder();
        out.append(String.format(java.util.Locale.ROOT, "FRT-%04d-", index));
        int tail = index % 11;
        for (int k = 0; k < tail; k++) {
            out.append((char) ('a' + ((index * 7 + k * 3) % 26)));
        }
        return out.toString();
    }

    public static long[] probeSeries(int series) {
        long[] values = new long[SERIES_LENGTH];
        for (int k = 0; k < SERIES_LENGTH; k++) {
            long m = Integer.toUnsignedLong(mix32(series * 977 + k * 31));
            values[k] = 3L + (m % 4093L);
        }
        return values;
    }

    public static List<ProbeRecord> probeRecords() {
        List<ProbeRecord> records = new ArrayList<ProbeRecord>();
        for (int index = 0; index < RECORD_COUNT; index++) {
            long m = Integer.toUnsignedLong(mix32(index * 131 + 17));
            records.add(new ProbeRecord(
                    String.format(java.util.Locale.ROOT, "RC-%03d", index),
                    m % 360L,
                    50L + ((m >>> 7) % 48000L),
                    (m >>> 3) % 5L,
                    (m >>> 11) % 9L,
                    6L + ((m >>> 17) % 7L)));
        }
        return records;
    }
}
