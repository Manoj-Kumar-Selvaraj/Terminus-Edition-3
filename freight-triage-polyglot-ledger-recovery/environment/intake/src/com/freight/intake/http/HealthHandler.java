package com.freight.intake.http;

import com.freight.json.JsonValue;

/** GET /v2/healthz - readiness probe used by the suite runner. */
public final class HealthHandler extends JsonHandler {

    @Override
    protected boolean requiresPost() {
        return false;
    }

    @Override
    protected JsonValue respond(String method, JsonValue body) {
        JsonValue out = JsonValue.object();
        out.put("schema_version", "freight-intake/2");
        out.put("status", "ok");
        return out;
    }
}
