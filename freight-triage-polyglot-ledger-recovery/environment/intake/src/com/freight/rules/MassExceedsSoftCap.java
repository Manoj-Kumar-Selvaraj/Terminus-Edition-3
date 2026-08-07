package com.freight.rules;

/** Triage predicate: mass exceeds soft cap. */
public final class MassExceedsSoftCap implements TriageRule {

    @Override
    public String name() {
        return "mass_exceeds_soft_cap";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.massKg > 18000;
    }
}
