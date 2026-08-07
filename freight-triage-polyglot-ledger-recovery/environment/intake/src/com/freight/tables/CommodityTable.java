package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback commodity registry mirrored across every language. */
public final class CommodityTable {

    /** One commodity row. */
    public static final class Row {

        public final String commodityCode;
        public final String groupCode;
        public final String description;
        public final long hazmatDefault;
        public final long densityKgM3;
        public final boolean stackable;

        public Row(String commodityCode, String groupCode, String description, long hazmatDefault, long densityKgM3, boolean stackable) {
            this.commodityCode = commodityCode;
            this.groupCode = groupCode;
            this.description = description;
            this.hazmatDefault = hazmatDefault;
            this.densityKgM3 = densityKgM3;
            this.stackable = stackable;
        }

        public String canonical() {
            return commodityCode + "|" + groupCode + "|" + description + "|" + hazmatDefault + "|" + densityKgM3 + "|" + (stackable ? "1" : "0");
        }
    }

    private static List<Row> cached;

    private CommodityTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            CommodityTableData00.fill(out);
            CommodityTableData01.fill(out);
            CommodityTableData02.fill(out);
            CommodityTableData03.fill(out);
            CommodityTableData04.fill(out);
            CommodityTableData05.fill(out);
            CommodityTableData06.fill(out);
            CommodityTableData07.fill(out);
            CommodityTableData08.fill(out);
            CommodityTableData09.fill(out);
            CommodityTableData10.fill(out);
            CommodityTableData11.fill(out);
            CommodityTableData12.fill(out);
            CommodityTableData13.fill(out);
            CommodityTableData14.fill(out);
            CommodityTableData15.fill(out);
            CommodityTableData16.fill(out);
            CommodityTableData17.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
