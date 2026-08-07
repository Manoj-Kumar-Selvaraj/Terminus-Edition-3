package com.freight.rules;

/** Triage predicate: seal length is canonical. */
public final class SealLengthIsCanonical implements TriageRule {

    @Override
    public String name() {
        return "seal_length_is_canonical";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.sealLength == 9;
    }
}
