package com.freight.intake.http;

import com.freight.intake.HoldStore;
import com.freight.intake.IntakeEvent;
import com.freight.json.JsonValue;

/** POST /v2/releases - release a previously accepted hold by reference. */
public final class ReleaseHandler extends JsonHandler {

    private final HoldStore store;

    public ReleaseHandler(HoldStore store) {
        this.store = store;
    }

    @Override
    protected JsonValue respond(String method, JsonValue body) {
        return store.releaseHold(IntakeEvent.fromJson(body));
    }
}
