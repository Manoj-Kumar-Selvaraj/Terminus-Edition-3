package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback hazmat registry mirrored across every language. */
public final class HazmatTable {

    /** One hazmat row. */
    public static final class Row {

        public final String ruleId;
        public final long hazmatClass;
        public final long minEscortPriority;
        public final String segregationCode;
        public final long maxSlotKg;

        public Row(String ruleId, long hazmatClass, long minEscortPriority, String segregationCode, long maxSlotKg) {
            this.ruleId = ruleId;
            this.hazmatClass = hazmatClass;
            this.minEscortPriority = minEscortPriority;
            this.segregationCode = segregationCode;
            this.maxSlotKg = maxSlotKg;
        }

        public String canonical() {
            return ruleId + "|" + hazmatClass + "|" + minEscortPriority + "|" + segregationCode + "|" + maxSlotKg;
        }
    }

    private static List<Row> cached;

    private HazmatTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            HazmatTableData00.fill(out);
            HazmatTableData01.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
