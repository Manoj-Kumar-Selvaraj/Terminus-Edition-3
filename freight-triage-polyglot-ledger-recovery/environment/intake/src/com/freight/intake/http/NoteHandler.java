package com.freight.intake.http;

import com.freight.intake.HoldStore;
import com.freight.intake.IntakeEvent;
import com.freight.json.JsonValue;

/** POST /v2/notes - attach an operational note to a manifest. */
public final class NoteHandler extends JsonHandler {

    private final HoldStore store;

    public NoteHandler(HoldStore store) {
        this.store = store;
    }

    @Override
    protected JsonValue respond(String method, JsonValue body) {
        return store.recordNote(IntakeEvent.fromJson(body));
    }
}
