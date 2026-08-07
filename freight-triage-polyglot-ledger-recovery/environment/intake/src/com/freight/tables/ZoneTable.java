package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback zone registry mirrored across every language. */
public final class ZoneTable {

    /** One zone row. */
    public static final class Row {

        public final String zoneKey;
        public final String abbrev;
        public final long offsetMinutes;
        public final long dstShiftMinutes;
        public final String hub;

        public Row(String zoneKey, String abbrev, long offsetMinutes, long dstShiftMinutes, String hub) {
            this.zoneKey = zoneKey;
            this.abbrev = abbrev;
            this.offsetMinutes = offsetMinutes;
            this.dstShiftMinutes = dstShiftMinutes;
            this.hub = hub;
        }

        public String canonical() {
            return zoneKey + "|" + abbrev + "|" + offsetMinutes + "|" + dstShiftMinutes + "|" + hub;
        }
    }

    private static List<Row> cached;

    private ZoneTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            ZoneTableData00.fill(out);
            ZoneTableData01.fill(out);
            ZoneTableData02.fill(out);
            ZoneTableData03.fill(out);
            ZoneTableData04.fill(out);
            ZoneTableData05.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
