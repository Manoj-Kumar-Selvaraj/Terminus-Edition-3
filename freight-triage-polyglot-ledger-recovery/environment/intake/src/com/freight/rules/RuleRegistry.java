package com.freight.rules;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of triage rules. */
public final class RuleRegistry {

    private RuleRegistry() {
    }

    public static List<TriageRule> all() {
        List<TriageRule> registry = new ArrayList<TriageRule>();
        registry.add(new LaneIndexInRange());
        registry.add(new MassWithinSlotBand());
        registry.add(new PriorityIsExpedite());
        registry.add(new HazmatRequiresEscort());
        registry.add(new SealLengthIsCanonical());
        registry.add(new MassIsMultipleOfTen());
        registry.add(new LaneIsCrossDock());
        registry.add(new PriorityMatchesHazmat());
        registry.add(new MassExceedsSoftCap());
        registry.add(new SealAndLaneParity());
        registry.add(new RecordIsAuditable());
        registry.add(new RecordNeedsManualTriage());
        return Collections.unmodifiableList(registry);
    }
}
