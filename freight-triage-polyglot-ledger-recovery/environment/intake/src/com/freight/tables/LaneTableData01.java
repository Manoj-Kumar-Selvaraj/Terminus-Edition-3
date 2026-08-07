package com.freight.tables;

import java.util.List;

/** lane rows 60..119. */
final class LaneTableData01 {

    private LaneTableData01() {
    }

    static void fill(List<LaneTable.Row> out) {
        out.add(new LaneTable.Row("LN-060", "NSH", "KCK", "intermodal", 1L, 15500L, 1260L, false));
        out.add(new LaneTable.Row("LN-061", "MSP", "NSH", "standard", 2L, 17000L, 1305L, false));
        out.add(new LaneTable.Row("LN-062", "DTW", "HOU", "flatbed", 3L, 18500L, 1350L, false));
        out.add(new LaneTable.Row("LN-063", "YYZ", "OKC", "reefer", 4L, 20000L, 1395L, true));
        out.add(new LaneTable.Row("LN-064", "SEA", "NSH", "reefer", 5L, 21500L, 1440L, false));
        out.add(new LaneTable.Row("LN-065", "OKC", "BOS", "expedite", 6L, 23000L, 1485L, false));
        out.add(new LaneTable.Row("LN-066", "LAX", "PHX", "expedite", 1L, 8000L, 1530L, false));
        out.add(new LaneTable.Row("LN-067", "STL", "HOU", "expedite", 2L, 9500L, 1575L, false));
        out.add(new LaneTable.Row("LN-068", "MSP", "ATL", "flatbed", 3L, 11000L, 1620L, false));
        out.add(new LaneTable.Row("LN-069", "CHI", "OKC", "bonded", 4L, 12500L, 1665L, false));
        out.add(new LaneTable.Row("LN-070", "YVR", "NSH", "bonded", 5L, 14000L, 1710L, true));
        out.add(new LaneTable.Row("LN-071", "RNO", "DTW", "reefer", 6L, 15500L, 1755L, false));
        out.add(new LaneTable.Row("LN-072", "CHI", "MEM", "intermodal", 1L, 17000L, 1800L, false));
        out.add(new LaneTable.Row("LN-073", "STL", "IND", "reefer", 2L, 18500L, 1845L, false));
        out.add(new LaneTable.Row("LN-074", "HOU", "KCK", "intermodal", 3L, 20000L, 1890L, false));
        out.add(new LaneTable.Row("LN-075", "DFW", "DFW", "standard", 4L, 21500L, 1935L, false));
        out.add(new LaneTable.Row("LN-076", "IND", "KCK", "reefer", 5L, 23000L, 1980L, false));
        out.add(new LaneTable.Row("LN-077", "TPA", "STL", "intermodal", 6L, 8000L, 2025L, true));
        out.add(new LaneTable.Row("LN-078", "IND", "KCK", "bonded", 1L, 9500L, 2070L, false));
        out.add(new LaneTable.Row("LN-079", "DEN", "JAX", "bonded", 2L, 11000L, 2115L, false));
        out.add(new LaneTable.Row("LN-080", "LAX", "PHX", "intermodal", 3L, 12500L, 360L, false));
        out.add(new LaneTable.Row("LN-081", "CHI", "YVR", "expedite", 4L, 14000L, 405L, false));
        out.add(new LaneTable.Row("LN-082", "JAX", "NSH", "bonded", 5L, 15500L, 450L, false));
        out.add(new LaneTable.Row("LN-083", "STL", "YYZ", "expedite", 6L, 17000L, 495L, false));
        out.add(new LaneTable.Row("LN-084", "LAX", "LAX", "reefer", 1L, 18500L, 540L, true));
        out.add(new LaneTable.Row("LN-085", "DFW", "HOU", "expedite", 2L, 20000L, 585L, false));
        out.add(new LaneTable.Row("LN-086", "SLC", "BOS", "standard", 3L, 21500L, 630L, false));
        out.add(new LaneTable.Row("LN-087", "LAX", "CHI", "expedite", 4L, 23000L, 675L, false));
        out.add(new LaneTable.Row("LN-088", "DEN", "BOS", "standard", 5L, 8000L, 720L, false));
        out.add(new LaneTable.Row("LN-089", "SEA", "STL", "intermodal", 6L, 9500L, 765L, false));
        out.add(new LaneTable.Row("LN-090", "PDX", "STL", "expedite", 1L, 11000L, 810L, false));
        out.add(new LaneTable.Row("LN-091", "OKC", "BOS", "flatbed", 2L, 12500L, 855L, true));
        out.add(new LaneTable.Row("LN-092", "NSH", "LAX", "reefer", 3L, 14000L, 900L, false));
        out.add(new LaneTable.Row("LN-093", "KCK", "ATL", "reefer", 4L, 15500L, 945L, false));
        out.add(new LaneTable.Row("LN-094", "ATL", "STL", "expedite", 5L, 17000L, 990L, false));
        out.add(new LaneTable.Row("LN-095", "KCK", "SEA", "flatbed", 6L, 18500L, 1035L, false));
        out.add(new LaneTable.Row("LN-096", "CHI", "LAX", "intermodal", 1L, 20000L, 1080L, false));
        out.add(new LaneTable.Row("LN-097", "DTW", "OKC", "standard", 2L, 21500L, 1125L, false));
        out.add(new LaneTable.Row("LN-098", "BOS", "STL", "flatbed", 3L, 23000L, 1170L, true));
        out.add(new LaneTable.Row("LN-099", "DTW", "OKC", "bonded", 4L, 8000L, 1215L, false));
        out.add(new LaneTable.Row("LN-100", "CHI", "BOS", "standard", 5L, 9500L, 1260L, false));
        out.add(new LaneTable.Row("LN-101", "CHI", "RNO", "flatbed", 6L, 11000L, 1305L, false));
        out.add(new LaneTable.Row("LN-102", "PHX", "DTW", "reefer", 1L, 12500L, 1350L, false));
        out.add(new LaneTable.Row("LN-103", "MSP", "LAX", "bonded", 2L, 14000L, 1395L, false));
        out.add(new LaneTable.Row("LN-104", "PDX", "CHI", "flatbed", 3L, 15500L, 1440L, false));
        out.add(new LaneTable.Row("LN-105", "TPA", "BOS", "flatbed", 4L, 17000L, 1485L, true));
        out.add(new LaneTable.Row("LN-106", "MSP", "STL", "intermodal", 5L, 18500L, 1530L, false));
        out.add(new LaneTable.Row("LN-107", "OKC", "LAX", "bonded", 6L, 20000L, 1575L, false));
        out.add(new LaneTable.Row("LN-108", "LAX", "YYZ", "bonded", 1L, 21500L, 1620L, false));
        out.add(new LaneTable.Row("LN-109", "JAX", "PHX", "expedite", 2L, 23000L, 1665L, false));
        out.add(new LaneTable.Row("LN-110", "SLC", "CHI", "standard", 3L, 8000L, 1710L, false));
        out.add(new LaneTable.Row("LN-111", "HOU", "SLC", "flatbed", 4L, 9500L, 1755L, false));
        out.add(new LaneTable.Row("LN-112", "STL", "PDX", "reefer", 5L, 11000L, 1800L, true));
        out.add(new LaneTable.Row("LN-113", "MSP", "OKC", "reefer", 6L, 12500L, 1845L, false));
        out.add(new LaneTable.Row("LN-114", "NSH", "YYZ", "intermodal", 1L, 14000L, 1890L, false));
        out.add(new LaneTable.Row("LN-115", "IND", "SLC", "flatbed", 2L, 15500L, 1935L, false));
        out.add(new LaneTable.Row("LN-116", "PHX", "JAX", "standard", 3L, 17000L, 1980L, false));
        out.add(new LaneTable.Row("LN-117", "TPA", "KCK", "intermodal", 4L, 18500L, 2025L, false));
        out.add(new LaneTable.Row("LN-118", "SLC", "HOU", "flatbed", 5L, 20000L, 2070L, false));
        out.add(new LaneTable.Row("LN-119", "BOS", "DFW", "flatbed", 6L, 21500L, 2115L, true));
    }
}
