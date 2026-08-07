package com.freight.rules;

/** Triage predicate: hazmat requires escort. */
public final class HazmatRequiresEscort implements TriageRule {

    @Override
    public String name() {
        return "hazmat_requires_escort";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.hazmatClass >= 3 && record.priority < 2;
    }
}
