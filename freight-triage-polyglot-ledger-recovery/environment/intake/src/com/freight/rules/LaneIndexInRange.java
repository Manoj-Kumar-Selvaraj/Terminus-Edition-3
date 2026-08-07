package com.freight.rules;

/** Triage predicate: lane index in range. */
public final class LaneIndexInRange implements TriageRule {

    @Override
    public String name() {
        return "lane_index_in_range";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.laneIndex >= 0 && record.laneIndex < 360;
    }
}
