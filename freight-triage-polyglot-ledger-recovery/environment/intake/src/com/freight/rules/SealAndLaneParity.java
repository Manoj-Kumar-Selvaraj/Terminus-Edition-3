package com.freight.rules;

/** Triage predicate: seal and lane parity. */
public final class SealAndLaneParity implements TriageRule {

    @Override
    public String name() {
        return "seal_and_lane_parity";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return (record.sealLength + record.laneIndex) % 2 == 0;
    }
}
