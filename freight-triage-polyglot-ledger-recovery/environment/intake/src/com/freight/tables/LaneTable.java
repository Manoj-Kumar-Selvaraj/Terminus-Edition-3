package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback lane registry mirrored across every language. */
public final class LaneTable {

    /** One lane row. */
    public static final class Row {

        public final String laneId;
        public final String originHub;
        public final String destHub;
        public final String serviceClass;
        public final long slotCount;
        public final long slotCapacityKg;
        public final long transitMinutes;
        public final boolean crossDock;

        public Row(String laneId, String originHub, String destHub, String serviceClass, long slotCount, long slotCapacityKg, long transitMinutes, boolean crossDock) {
            this.laneId = laneId;
            this.originHub = originHub;
            this.destHub = destHub;
            this.serviceClass = serviceClass;
            this.slotCount = slotCount;
            this.slotCapacityKg = slotCapacityKg;
            this.transitMinutes = transitMinutes;
            this.crossDock = crossDock;
        }

        public String canonical() {
            return laneId + "|" + originHub + "|" + destHub + "|" + serviceClass + "|" + slotCount + "|" + slotCapacityKg + "|" + transitMinutes + "|" + (crossDock ? "1" : "0");
        }
    }

    private static List<Row> cached;

    private LaneTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            LaneTableData00.fill(out);
            LaneTableData01.fill(out);
            LaneTableData02.fill(out);
            LaneTableData03.fill(out);
            LaneTableData04.fill(out);
            LaneTableData05.fill(out);
            LaneTableData06.fill(out);
            LaneTableData07.fill(out);
            LaneTableData08.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
