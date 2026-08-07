package com.freight.tables;

import java.util.List;

/** zone rows 300..319. */
final class ZoneTableData05 {

    private ZoneTableData05() {
    }

    static void fill(List<ZoneTable.Row> out) {
        out.add(new ZoneTable.Row("FZ-300", "Z00O", -480L, 60L, "MSP"));
        out.add(new ZoneTable.Row("FZ-301", "Z01P", -420L, 0L, "NSH"));
        out.add(new ZoneTable.Row("FZ-302", "Z02Q", -360L, 0L, "OKC"));
        out.add(new ZoneTable.Row("FZ-303", "Z03R", -300L, 0L, "PDX"));
        out.add(new ZoneTable.Row("FZ-304", "Z04S", -240L, 60L, "PHX"));
        out.add(new ZoneTable.Row("FZ-305", "Z05T", -210L, 0L, "RNO"));
        out.add(new ZoneTable.Row("FZ-306", "Z06U", -180L, 0L, "SLC"));
        out.add(new ZoneTable.Row("FZ-307", "Z07V", -120L, 0L, "SEA"));
        out.add(new ZoneTable.Row("FZ-308", "Z08W", -60L, 60L, "STL"));
        out.add(new ZoneTable.Row("FZ-309", "Z09X", 0L, 0L, "TPA"));
        out.add(new ZoneTable.Row("FZ-310", "Z10Y", 60L, 0L, "YYZ"));
        out.add(new ZoneTable.Row("FZ-311", "Z11Z", 120L, 0L, "YVR"));
        out.add(new ZoneTable.Row("FZ-312", "Z12A", 180L, 60L, "ATL"));
        out.add(new ZoneTable.Row("FZ-313", "Z13B", 210L, 0L, "BOS"));
        out.add(new ZoneTable.Row("FZ-314", "Z14C", 240L, 0L, "CHI"));
        out.add(new ZoneTable.Row("FZ-315", "Z15D", 270L, 0L, "DFW"));
        out.add(new ZoneTable.Row("FZ-316", "Z16E", 300L, 60L, "DEN"));
        out.add(new ZoneTable.Row("FZ-317", "Z17F", 330L, 0L, "DTW"));
        out.add(new ZoneTable.Row("FZ-318", "Z18G", 345L, 0L, "HOU"));
        out.add(new ZoneTable.Row("FZ-319", "Z19H", 360L, 0L, "IND"));
    }
}
