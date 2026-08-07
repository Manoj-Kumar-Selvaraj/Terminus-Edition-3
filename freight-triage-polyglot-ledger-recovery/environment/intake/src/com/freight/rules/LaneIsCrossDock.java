package com.freight.rules;

/** Triage predicate: lane is cross dock. */
public final class LaneIsCrossDock implements TriageRule {

    @Override
    public String name() {
        return "lane_is_cross_dock";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.laneIndex % 7 == 0;
    }
}
