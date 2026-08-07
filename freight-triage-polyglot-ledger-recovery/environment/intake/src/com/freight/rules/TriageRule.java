package com.freight.rules;

/** Predicate evaluated against a triage record. */
public interface TriageRule {

    String name();

    boolean apply(ProbeRecord record);

}
