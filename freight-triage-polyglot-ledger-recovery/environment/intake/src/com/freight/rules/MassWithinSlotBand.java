package com.freight.rules;

/** Triage predicate: mass within slot band. */
public final class MassWithinSlotBand implements TriageRule {

    @Override
    public String name() {
        return "mass_within_slot_band";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.massKg >= 500 && record.massKg <= 24000;
    }
}
