package io.jenkins.plugins.insights.journal;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Event;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class JournalMaintenance {
    public record Inspection(long firstSequence, long lastSequence, int events, int duplicateIds,
                             int sequenceGaps, boolean tornTail, String digest, List<String> diagnostics) {
        public boolean healthy() { return !tornTail && duplicateIds == 0 && sequenceGaps == 0 && diagnostics.isEmpty(); }
        public Map<String, Object> toMap() { return Domain.ordered("firstSequence", firstSequence, "lastSequence", lastSequence,
                "events", events, "duplicateIds", duplicateIds, "sequenceGaps", sequenceGaps, "tornTail", tornTail,
                "digest", digest, "healthy", healthy(), "diagnostics", diagnostics); }
    }
    public record Compaction(int before, int after, long checkpoint, String digest) {}

    public Inspection inspect(Path journal) throws IOException {
        EventJournal.Recovery recovery = EventJournal.recover(journal, -1);
        long first = recovery.events().isEmpty() ? 0 : recovery.events().get(0).sequence();
        long last = recovery.lastGoodSequence(); int duplicates = 0; int gaps = 0;
        long expected = first; Set<String> identities = new HashSet<>(); List<String> diagnostics = new ArrayList<>(recovery.diagnostics());
        for (Event event : recovery.events()) {
            if (!identities.add(event.eventId())) duplicates++;
            if (event.sequence() != expected) { gaps++; expected = event.sequence(); }
            expected++;
            if (!Domain.sha256(io.jenkins.plugins.insights.json.Json.write(event.payload())).equals(event.payloadHash()))
                diagnostics.add("payload digest mismatch at sequence " + event.sequence());
        }
        String digest = Domain.sha256(io.jenkins.plugins.insights.json.Json.write(recovery.events().stream().map(Event::toMap).toList()));
        return new Inspection(first, last, recovery.events().size(), duplicates, gaps, recovery.tornTail(), digest, List.copyOf(diagnostics));
    }

    public Compaction compact(Path journal, long checkpoint) throws IOException {
        EventJournal.Recovery all = EventJournal.recover(journal, -1);
        if (all.tornTail()) throw new IOException("cannot compact an invalid journal tail");
        List<Event> retained = all.events().stream().filter(event -> event.sequence() > checkpoint).toList();
        Path temporary = journal.resolveSibling(journal.getFileName() + ".compact"); List<String> lines = new ArrayList<>(retained.size());
        for (Event event : retained) {
            Map<String, Object> envelope = new java.util.LinkedHashMap<>(event.toMap());
            envelope.put("checksum", Domain.sha256(io.jenkins.plugins.insights.json.Json.write(event.toMap())));
            lines.add(io.jenkins.plugins.insights.json.Json.write(envelope));
        }
        Files.write(temporary, lines, StandardCharsets.UTF_8);
        Files.move(temporary, journal, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        return new Compaction(all.events().size(), retained.size(), checkpoint, Domain.sha256(String.join("\n", lines)));
    }
}