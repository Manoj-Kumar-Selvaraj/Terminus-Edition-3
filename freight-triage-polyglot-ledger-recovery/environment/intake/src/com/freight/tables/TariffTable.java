package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback tariff registry mirrored across every language. */
public final class TariffTable {

    /** One tariff row. */
    public static final class Row {

        public final String groupCode;
        public final String band;
        public final long rateCents;

        public Row(String groupCode, String band, long rateCents) {
            this.groupCode = groupCode;
            this.band = band;
            this.rateCents = rateCents;
        }

        public String canonical() {
            return groupCode + "|" + band + "|" + rateCents;
        }
    }

    private static List<Row> cached;

    private TariffTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            TariffTableData00.fill(out);
            TariffTableData01.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
