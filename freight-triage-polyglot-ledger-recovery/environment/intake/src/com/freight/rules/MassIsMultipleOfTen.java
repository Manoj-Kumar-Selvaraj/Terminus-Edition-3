package com.freight.rules;

/** Triage predicate: mass is multiple of ten. */
public final class MassIsMultipleOfTen implements TriageRule {

    @Override
    public String name() {
        return "mass_is_multiple_of_ten";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.massKg % 10 == 0;
    }
}
