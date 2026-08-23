package io.jenkins.plugins.insights.reconcile;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Event;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Normalizes a bounded listener batch before applying canonical transitions. */
public final class EventBatchPlanner {
    public record Rejected(String eventId, long sequence, String reason) {
        public Map<String, Object> toMap() { return Domain.ordered("eventId", eventId, "sequence", sequence, "reason", reason); }
    }
    public record Batch(List<Event> events, List<Rejected> rejected, Set<SourceKind> dirtySources,
                        long firstSequence, long lastSequence, String digest) {
        public Map<String, Object> toMap() {
            return Domain.ordered("events", events.stream().map(Event::toMap).toList(),
                    "rejected", rejected.stream().map(Rejected::toMap).toList(),
                    "dirtySources", dirtySources.stream().map(Enum::name).sorted().toList(),
                    "firstSequence", firstSequence, "lastSequence", lastSequence, "digest", digest);
        }
    }

    public Batch plan(Collection<Event> input, long checkpoint, int maximum) {
        if (maximum < 1) throw new IllegalArgumentException("maximum must be positive");
        List<Event> ordered = input.stream().sorted(Comparator.comparingLong(Event::sequence)
                .thenComparing(Event::eventId)).limit(maximum).toList();
        List<Event> accepted = new ArrayList<>(); List<Rejected> rejected = new ArrayList<>();
        Set<SourceKind> dirty = new LinkedHashSet<>(); Map<String, Event> identities = new HashMap<>();
        Map<String, Event> latestByRecord = new LinkedHashMap<>();
        long first = 0; long last = checkpoint;
        for (Event event : ordered) {
            if (event.sequence() <= checkpoint) { rejected.add(new Rejected(event.eventId(), event.sequence(), "represented by checkpoint")); continue; }
            Event identity = identities.putIfAbsent(event.eventId(), event);
            if (identity != null) {
                rejected.add(new Rejected(event.eventId(), event.sequence(), "duplicate event identity")); continue;
            }
            if (first == 0) first = event.sequence(); last = Math.max(last, event.sequence());
            if (event.operation() == EventOperation.DIRTY) { dirty.add(event.source()); accepted.add(event); continue; }
            String record = event.source().name() + ":" + event.recordKey(); Event prior = latestByRecord.get(record);
            if (prior == null || event.sequence() >= prior.sequence()) latestByRecord.put(record, event);
            else rejected.add(new Rejected(event.eventId(), event.sequence(), "older record transition"));
        }
        accepted.addAll(latestByRecord.values());
        accepted.sort(Comparator.comparingLong(Event::sequence).thenComparing(Event::eventId));
        String digest = Domain.sha256(io.jenkins.plugins.insights.json.Json.write(accepted.stream().map(Event::toMap).toList()));
        return new Batch(List.copyOf(accepted), List.copyOf(rejected), Set.copyOf(dirty), first, last, digest);
    }

    public Map<SourceKind, Integer> counts(Batch batch) {
        Map<SourceKind, Integer> result = new EnumMap<>(SourceKind.class);
        for (Event event : batch.events()) result.merge(event.source(), 1, Integer::sum); return Map.copyOf(result);
    }

    public boolean contiguous(Batch batch, long checkpoint) {
        long expected = checkpoint + 1;
        for (Event event : batch.events()) {
            if (event.sequence() != expected) return false; expected++;
        }
        return true;
    }
}
