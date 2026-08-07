package com.freight.rules;

/** Synthetic triage record used by the cross language conformance probe. */
public final class ProbeRecord {

    public final String recordId;
    public final long laneIndex;
    public final long massKg;
    public final long priority;
    public final long hazmatClass;
    public final long sealLength;

    public ProbeRecord(String recordId, long laneIndex, long massKg, long priority,
                       long hazmatClass, long sealLength) {
        this.recordId = recordId;
        this.laneIndex = laneIndex;
        this.massKg = massKg;
        this.priority = priority;
        this.hazmatClass = hazmatClass;
        this.sealLength = sealLength;
    }
}
