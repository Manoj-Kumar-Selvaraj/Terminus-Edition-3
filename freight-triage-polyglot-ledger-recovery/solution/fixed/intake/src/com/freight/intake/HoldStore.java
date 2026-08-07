package com.freight.intake;

import com.freight.json.JsonValue;
import com.freight.util.FreightTime;
import com.freight.util.SealDigest;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Authoritative in-memory hold ledger behind the intake HTTP API.
 *
 * All mutating entry points are synchronized so concurrent hold placements on
 * the same manifest are serialized.
 */
public final class HoldStore {

    /** A hold that has been placed and not yet released. */
    public static final class OpenHold {
        public final long ref;
        public final String manifestId;
        public final long kilograms;
        public boolean released;

        OpenHold(long ref, String manifestId, long kilograms) {
            this.ref = ref;
            this.manifestId = manifestId;
            this.kilograms = kilograms;
            this.released = false;
        }
    }

    /** Rolling per-manifest hold aggregate. */
    public static final class ManifestHolds {
        public final String manifestId;
        public String seal = "";
        public long heldKg;
        public long releasedKg;
        public long openHolds;
        public long firstHoldEpochS = Long.MAX_VALUE;
        public long lastEventEpochS = Long.MIN_VALUE;

        ManifestHolds(String manifestId) {
            this.manifestId = manifestId;
        }
    }

    /** One durable journal row. */
    public static final class JournalRow {
        public final long seq;
        public final String kind;
        public final String manifestId;
        public final long atEpochS;
        public final boolean accepted;
        public final String code;
        public final long ref;
        public final long tonnesKg;

        JournalRow(long seq, String kind, String manifestId, long atEpochS, boolean accepted,
                   String code, long ref, long tonnesKg) {
            this.seq = seq;
            this.kind = kind;
            this.manifestId = manifestId;
            this.atEpochS = atEpochS;
            this.accepted = accepted;
            this.code = code;
            this.ref = ref;
            this.tonnesKg = tonnesKg;
        }

        public String canonical() {
            return seq + "|" + kind + "|" + manifestId + "|" + atEpochS + "|"
                    + (accepted ? "1" : "0") + "|" + code + "|" + ref + "|" + tonnesKg + "\n";
        }
    }

    private final Map<Long, OpenHold> openByRef = new TreeMap<Long, OpenHold>();
    private final Map<String, ManifestHolds> byManifest = new LinkedHashMap<String, ManifestHolds>();
    private final List<JournalRow> journal = new ArrayList<JournalRow>();

    private ManifestHolds holdsFor(String manifestId) {
        ManifestHolds holds = byManifest.get(manifestId);
        if (holds == null) {
            holds = new ManifestHolds(manifestId);
            byManifest.put(manifestId, holds);
        }
        return holds;
    }

    private void appendJournal(IntakeEvent event, boolean accepted, String code, long ref) {
        long epochSeconds = FreightTime.parseEpochSeconds(event.atLocal);
        journal.add(new JournalRow(event.seq, event.kind, event.manifestId, epochSeconds, accepted,
                code, ref, event.tonnesKg));
    }

    private static JsonValue reply(boolean accepted, String code, long ref) {
        JsonValue out = JsonValue.object();
        out.put("accepted", accepted);
        out.put("code", code);
        out.put("ref", ref);
        return out;
    }

    private void recordAcceptedHold(IntakeEvent event, OpenHold open) {
        appendJournal(event, true, "HOLD_PLACED", open.ref);
    }

    public synchronized JsonValue placeHold(IntakeEvent event) {
        if (event.manifestId == null || event.manifestId.isEmpty()) {
            appendJournal(event, false, "HOLD_MISSING_MANIFEST", 0L);
            return reply(false, "HOLD_MISSING_MANIFEST", 0L);
        }
        if (event.tonnesKg <= 0L) {
            appendJournal(event, false, "HOLD_INVALID_TONNES", 0L);
            return reply(false, "HOLD_INVALID_TONNES", 0L);
        }

        OpenHold open = new OpenHold(event.seq, event.manifestId, event.tonnesKg);
        openByRef.put(Long.valueOf(event.seq), open);

        ManifestHolds holds = holdsFor(event.manifestId);
        holds.heldKg += event.tonnesKg;
        holds.openHolds += 1L;
        if (holds.seal.isEmpty()) {
            holds.seal = SealDigest.normalize(event.seal);
        }
        long epochSeconds = FreightTime.parseEpochSeconds(event.atLocal);
        if (epochSeconds < holds.firstHoldEpochS) {
            holds.firstHoldEpochS = epochSeconds;
        }
        if (epochSeconds > holds.lastEventEpochS) {
            holds.lastEventEpochS = epochSeconds;
        }

        recordAcceptedHold(event, open);
        return reply(true, "HOLD_PLACED", open.ref);
    }

    public synchronized JsonValue releaseHold(IntakeEvent event) {
        OpenHold open = openByRef.get(Long.valueOf(event.holdRef));
        if (open == null) {
            appendJournal(event, false, "RELEASE_UNKNOWN_REF", event.holdRef);
            return reply(false, "RELEASE_UNKNOWN_REF", event.holdRef);
        }
        if (open.released) {
            appendJournal(event, false, "RELEASE_ALREADY_CLOSED", event.holdRef);
            return reply(false, "RELEASE_ALREADY_CLOSED", event.holdRef);
        }
        open.released = true;

        ManifestHolds holds = holdsFor(open.manifestId);
        holds.releasedKg += open.kilograms;
        holds.openHolds -= 1L;
        long epochSeconds = FreightTime.parseEpochSeconds(event.atLocal);
        if (epochSeconds > holds.lastEventEpochS) {
            holds.lastEventEpochS = epochSeconds;
        }

        appendJournal(event, true, "RELEASE_APPLIED", event.holdRef);
        return reply(true, "RELEASE_APPLIED", event.holdRef);
    }

    public synchronized JsonValue recordNote(IntakeEvent event) {
        appendJournal(event, true, "NOTE_RECORDED", 0L);
        if (event.manifestId != null && !event.manifestId.isEmpty()) {
            ManifestHolds holds = byManifest.get(event.manifestId);
            if (holds != null) {
                long epochSeconds = FreightTime.parseEpochSeconds(event.atLocal);
                if (epochSeconds > holds.lastEventEpochS) {
                    holds.lastEventEpochS = epochSeconds;
                }
            }
        }
        return reply(true, "NOTE_RECORDED", 0L);
    }

    public synchronized List<JournalRow> journalRows() {
        List<JournalRow> copy = new ArrayList<JournalRow>(journal);
        copy.sort(new java.util.Comparator<JournalRow>() {
            @Override
            public int compare(JournalRow left, JournalRow right) {
                return Long.compare(left.seq, right.seq);
            }
        });
        return copy;
    }

    public synchronized List<ManifestHolds> holdAggregates() {
        return new ArrayList<ManifestHolds>(byManifest.values());
    }
}
