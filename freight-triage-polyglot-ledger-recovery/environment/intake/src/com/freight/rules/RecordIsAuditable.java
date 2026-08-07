package com.freight.rules;

/** Triage predicate: record is auditable. */
public final class RecordIsAuditable implements TriageRule {

    @Override
    public String name() {
        return "record_is_auditable";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return new LaneIndexInRange().apply(record) && new SealLengthIsCanonical().apply(record) && !new MassExceedsSoftCap().apply(record);
    }
}
