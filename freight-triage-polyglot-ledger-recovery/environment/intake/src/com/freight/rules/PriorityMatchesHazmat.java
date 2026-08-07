package com.freight.rules;

/** Triage predicate: priority matches hazmat. */
public final class PriorityMatchesHazmat implements TriageRule {

    @Override
    public String name() {
        return "priority_matches_hazmat";
    }

    @Override
    public boolean apply(ProbeRecord record) {
        return record.priority == record.hazmatClass % 5;
    }
}
