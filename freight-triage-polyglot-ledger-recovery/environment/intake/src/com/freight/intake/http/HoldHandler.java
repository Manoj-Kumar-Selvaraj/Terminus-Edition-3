package com.freight.intake.http;

import com.freight.intake.HoldStore;
import com.freight.intake.IntakeEvent;
import com.freight.json.JsonValue;

/** POST /v2/holds - place a tonnage hold against a manifest. */
public final class HoldHandler extends JsonHandler {

    private final HoldStore store;

    public HoldHandler(HoldStore store) {
        this.store = store;
    }

    @Override
    protected JsonValue respond(String method, JsonValue body) {
        return store.placeHold(IntakeEvent.fromJson(body));
    }
}
