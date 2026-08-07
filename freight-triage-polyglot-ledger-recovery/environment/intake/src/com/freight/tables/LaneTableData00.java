package com.freight.tables;

import java.util.List;

/** lane rows 0..59. */
final class LaneTableData00 {

    private LaneTableData00() {
    }

    static void fill(List<LaneTable.Row> out) {
        out.add(new LaneTable.Row("LN-000", "HOU", "PDX", "standard", 1L, 8000L, 360L, true));
        out.add(new LaneTable.Row("LN-001", "IND", "OKC", "standard", 2L, 9500L, 405L, false));
        out.add(new LaneTable.Row("LN-002", "CHI", "DTW", "flatbed", 3L, 11000L, 450L, false));
        out.add(new LaneTable.Row("LN-003", "IND", "MSP", "reefer", 4L, 12500L, 495L, false));
        out.add(new LaneTable.Row("LN-004", "PHX", "PDX", "intermodal", 5L, 14000L, 540L, false));
        out.add(new LaneTable.Row("LN-005", "SLC", "OKC", "standard", 6L, 15500L, 585L, false));
        out.add(new LaneTable.Row("LN-006", "YVR", "NSH", "bonded", 1L, 17000L, 630L, false));
        out.add(new LaneTable.Row("LN-007", "NSH", "NSH", "intermodal", 2L, 18500L, 675L, true));
        out.add(new LaneTable.Row("LN-008", "CHI", "PDX", "reefer", 3L, 20000L, 720L, false));
        out.add(new LaneTable.Row("LN-009", "JAX", "CHI", "expedite", 4L, 21500L, 765L, false));
        out.add(new LaneTable.Row("LN-010", "YVR", "LAX", "standard", 5L, 23000L, 810L, false));
        out.add(new LaneTable.Row("LN-011", "RNO", "RNO", "expedite", 6L, 8000L, 855L, false));
        out.add(new LaneTable.Row("LN-012", "ATL", "DTW", "expedite", 1L, 9500L, 900L, false));
        out.add(new LaneTable.Row("LN-013", "HOU", "DFW", "reefer", 2L, 11000L, 945L, false));
        out.add(new LaneTable.Row("LN-014", "SLC", "OKC", "reefer", 3L, 12500L, 990L, true));
        out.add(new LaneTable.Row("LN-015", "JAX", "RNO", "intermodal", 4L, 14000L, 1035L, false));
        out.add(new LaneTable.Row("LN-016", "DEN", "TPA", "expedite", 5L, 15500L, 1080L, false));
        out.add(new LaneTable.Row("LN-017", "RNO", "LAX", "standard", 6L, 17000L, 1125L, false));
        out.add(new LaneTable.Row("LN-018", "MSP", "PDX", "bonded", 1L, 18500L, 1170L, false));
        out.add(new LaneTable.Row("LN-019", "JAX", "JAX", "intermodal", 2L, 20000L, 1215L, false));
        out.add(new LaneTable.Row("LN-020", "RNO", "DFW", "expedite", 3L, 21500L, 1260L, false));
        out.add(new LaneTable.Row("LN-021", "KCK", "IND", "reefer", 4L, 23000L, 1305L, true));
        out.add(new LaneTable.Row("LN-022", "RNO", "MEM", "standard", 5L, 8000L, 1350L, false));
        out.add(new LaneTable.Row("LN-023", "DFW", "TPA", "flatbed", 6L, 9500L, 1395L, false));
        out.add(new LaneTable.Row("LN-024", "ATL", "TPA", "bonded", 1L, 11000L, 1440L, false));
        out.add(new LaneTable.Row("LN-025", "ATL", "IND", "standard", 2L, 12500L, 1485L, false));
        out.add(new LaneTable.Row("LN-026", "KCK", "DTW", "flatbed", 3L, 14000L, 1530L, false));
        out.add(new LaneTable.Row("LN-027", "JAX", "RNO", "expedite", 4L, 15500L, 1575L, false));
        out.add(new LaneTable.Row("LN-028", "YYZ", "CHI", "flatbed", 5L, 17000L, 1620L, true));
        out.add(new LaneTable.Row("LN-029", "STL", "RNO", "intermodal", 6L, 18500L, 1665L, false));
        out.add(new LaneTable.Row("LN-030", "RNO", "MSP", "bonded", 1L, 20000L, 1710L, false));
        out.add(new LaneTable.Row("LN-031", "LAX", "LAX", "standard", 2L, 21500L, 1755L, false));
        out.add(new LaneTable.Row("LN-032", "SLC", "JAX", "bonded", 3L, 23000L, 1800L, false));
        out.add(new LaneTable.Row("LN-033", "LAX", "OKC", "reefer", 4L, 8000L, 1845L, false));
        out.add(new LaneTable.Row("LN-034", "TPA", "MEM", "standard", 5L, 9500L, 1890L, false));
        out.add(new LaneTable.Row("LN-035", "STL", "YYZ", "flatbed", 6L, 11000L, 1935L, true));
        out.add(new LaneTable.Row("LN-036", "YVR", "BOS", "expedite", 1L, 12500L, 1980L, false));
        out.add(new LaneTable.Row("LN-037", "STL", "MEM", "reefer", 2L, 14000L, 2025L, false));
        out.add(new LaneTable.Row("LN-038", "YYZ", "YVR", "intermodal", 3L, 15500L, 2070L, false));
        out.add(new LaneTable.Row("LN-039", "CHI", "DFW", "standard", 4L, 17000L, 2115L, false));
        out.add(new LaneTable.Row("LN-040", "BOS", "TPA", "flatbed", 5L, 18500L, 360L, false));
        out.add(new LaneTable.Row("LN-041", "STL", "BOS", "flatbed", 6L, 20000L, 405L, false));
        out.add(new LaneTable.Row("LN-042", "PHX", "TPA", "intermodal", 1L, 21500L, 450L, true));
        out.add(new LaneTable.Row("LN-043", "RNO", "RNO", "expedite", 2L, 23000L, 495L, false));
        out.add(new LaneTable.Row("LN-044", "CHI", "PDX", "reefer", 3L, 8000L, 540L, false));
        out.add(new LaneTable.Row("LN-045", "PHX", "DTW", "flatbed", 4L, 9500L, 585L, false));
        out.add(new LaneTable.Row("LN-046", "HOU", "DFW", "reefer", 5L, 11000L, 630L, false));
        out.add(new LaneTable.Row("LN-047", "ATL", "SLC", "bonded", 6L, 12500L, 675L, false));
        out.add(new LaneTable.Row("LN-048", "SEA", "DTW", "flatbed", 1L, 14000L, 720L, false));
        out.add(new LaneTable.Row("LN-049", "YVR", "RNO", "intermodal", 2L, 15500L, 765L, true));
        out.add(new LaneTable.Row("LN-050", "STL", "KCK", "intermodal", 3L, 17000L, 810L, false));
        out.add(new LaneTable.Row("LN-051", "STL", "NSH", "standard", 4L, 18500L, 855L, false));
        out.add(new LaneTable.Row("LN-052", "OKC", "DEN", "flatbed", 5L, 20000L, 900L, false));
        out.add(new LaneTable.Row("LN-053", "TPA", "JAX", "reefer", 6L, 21500L, 945L, false));
        out.add(new LaneTable.Row("LN-054", "MSP", "DEN", "flatbed", 1L, 23000L, 990L, false));
        out.add(new LaneTable.Row("LN-055", "YVR", "TPA", "expedite", 2L, 8000L, 1035L, false));
        out.add(new LaneTable.Row("LN-056", "TPA", "YYZ", "flatbed", 3L, 9500L, 1080L, true));
        out.add(new LaneTable.Row("LN-057", "BOS", "TPA", "flatbed", 4L, 11000L, 1125L, false));
        out.add(new LaneTable.Row("LN-058", "TPA", "MSP", "reefer", 5L, 12500L, 1170L, false));
        out.add(new LaneTable.Row("LN-059", "MEM", "NSH", "standard", 6L, 14000L, 1215L, false));
    }
}
