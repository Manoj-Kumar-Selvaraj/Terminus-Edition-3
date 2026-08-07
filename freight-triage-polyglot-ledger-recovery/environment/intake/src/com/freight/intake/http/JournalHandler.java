package com.freight.intake.http;

import com.freight.intake.HoldStore;
import com.freight.intake.JournalWriter;
import com.freight.json.JsonValue;

/** GET /v2/journal - the durable intake journal in contract form. */
public final class JournalHandler extends JsonHandler {

    private final HoldStore store;

    public JournalHandler(HoldStore store) {
        this.store = store;
    }

    @Override
    protected boolean requiresPost() {
        return false;
    }

    @Override
    protected JsonValue respond(String method, JsonValue body) {
        return JournalWriter.build(store);
    }
}
