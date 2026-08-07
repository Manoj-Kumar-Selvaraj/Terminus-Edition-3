package com.freight.rules;

/** Triage predicate: record needs manual triage. */
public final class RecordNeedsManualTriage implements TriageRule {

    @Override
    public String name() {
        return "record_needs_manual_triage";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return new HazmatRequiresEscort().apply(record) || new MassExceedsSoftCap().apply(record) || !new LaneIndexInRange().apply(record);
    }
}
