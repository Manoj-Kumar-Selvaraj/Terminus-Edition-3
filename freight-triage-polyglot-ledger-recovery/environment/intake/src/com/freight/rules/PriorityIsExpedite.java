package com.freight.rules;

/** Triage predicate: priority is expedite. */
public final class PriorityIsExpedite implements TriageRule {

    @Override
    public String name() {
        return "priority_is_expedite";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.priority >= 3;
    }
}
