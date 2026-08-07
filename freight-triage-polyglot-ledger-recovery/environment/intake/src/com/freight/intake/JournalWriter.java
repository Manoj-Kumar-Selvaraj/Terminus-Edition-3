package com.freight.intake;

import com.freight.json.JsonValue;
import com.freight.util.FreightTime;
import com.freight.util.SealDigest;
import com.freight.util.Sha256Util;

import java.util.Comparator;
import java.util.List;

/** Serializes the hold store into the contracted intake journal document. */
public final class JournalWriter {

    private JournalWriter() {
    }

    public static JsonValue build(HoldStore store) {
        List<HoldStore.JournalRow> rows = store.journalRows();

        JsonValue events = JsonValue.array();
        Sha256Util hasher = new Sha256Util();
        long accepted = 0L;
        long rejected = 0L;
        for (HoldStore.JournalRow row : rows) {
            JsonValue event = JsonValue.object();
            event.put("accepted", row.accepted);
            event.put("at_epoch_s", row.atEpochS);
            event.put("code", row.code);
            event.put("kind", row.kind);
            event.put("manifest_id", row.manifestId);
            event.put("ref", row.ref);
            event.put("seq", row.seq);
            event.put("tonnes_kg", row.tonnesKg);
            events.add(event);
            hasher.update(row.canonical());
            if (row.accepted) {
                accepted += 1L;
            } else {
                rejected += 1L;
            }
        }

        // Aggregates are emitted in the order manifests first appeared on the wire.
        List<HoldStore.ManifestHolds> aggregates = store.holdAggregates();

        JsonValue holds = JsonValue.array();
        long heldKg = 0L;
        long releasedKg = 0L;
        long openHolds = 0L;
        for (HoldStore.ManifestHolds aggregate : aggregates) {
            long net = aggregate.heldKg - aggregate.releasedKg;
            JsonValue hold = JsonValue.object();
            hold.put("first_hold_epoch_s", aggregate.firstHoldEpochS);
            hold.put("held_kg", aggregate.heldKg);
            hold.put("held_tonnes", FreightTime.formatTonnes(aggregate.heldKg));
            hold.put("last_event_epoch_s", aggregate.lastEventEpochS);
            hold.put("manifest_ref", aggregate.manifestId);
            hold.put("net_held_kg", net);
            hold.put("net_held_tonnes", FreightTime.formatTonnes(net));
            hold.put("open_holds", aggregate.openHolds);
            hold.put("released_kg", aggregate.releasedKg);
            hold.put("seal", aggregate.seal);
            hold.put("seal_digest", SealDigest.digestHex(aggregate.seal));
            holds.add(hold);
            heldKg += aggregate.heldKg;
            releasedKg += aggregate.releasedKg;
            openHolds += aggregate.openHolds;
        }

        JsonValue totals = JsonValue.object();
        totals.put("accepted", accepted);
        totals.put("events", (long) rows.size());
        totals.put("held_kg", heldKg);
        totals.put("net_held_kg", heldKg - releasedKg);
        totals.put("open_holds", openHolds);
        totals.put("rejected", rejected);
        totals.put("released_kg", releasedKg);

        JsonValue journal = JsonValue.object();
        journal.put("epoch_base_s", FreightTime.EPOCH_BASE_S);
        journal.put("events", events);
        journal.put("generator", "freight-intake");
        journal.put("holds", holds);
        journal.put("journal_digest", hasher.hex());
        journal.put("schema_version", "freight-intake/2");
        journal.put("totals", totals);
        journal.put("window_seconds", FreightTime.WINDOW_SECONDS);
        return journal;
    }
}
