package com.freight.intake;

import com.freight.json.JsonValue;

/** One inbound intake request as posted to the HTTP API. */
public final class IntakeEvent {

    public final long seq;
    public final String kind;
    public final String manifestId;
    public final long tonnesKg;
    public final long holdRef;
    public final String reason;
    public final String seal;
    public final String atLocal;

    public IntakeEvent(long seq, String kind, String manifestId, long tonnesKg, long holdRef,
                       String reason, String seal, String atLocal) {
        this.seq = seq;
        this.kind = kind;
        this.manifestId = manifestId;
        this.tonnesKg = tonnesKg;
        this.holdRef = holdRef;
        this.reason = reason;
        this.seal = seal;
        this.atLocal = atLocal;
    }

    public static IntakeEvent fromJson(JsonValue value) {
        return new IntakeEvent(
                value.get("seq").asLong(0L),
                value.get("kind").asString(""),
                value.get("manifest_id").asString(""),
                value.get("tonnes_kg").asLong(0L),
                value.get("hold_ref").asLong(0L),
                value.get("reason").asString(""),
                value.get("seal").asString(""),
                value.get("at_local").asString(""));
    }

    public JsonValue toJson() {
        JsonValue out = JsonValue.object();
        out.put("at_local", atLocal);
        out.put("hold_ref", holdRef);
        out.put("kind", kind);
        out.put("manifest_id", manifestId);
        out.put("reason", reason);
        out.put("seal", seal);
        out.put("seq", seq);
        out.put("tonnes_kg", tonnesKg);
        return out;
    }

    public String endpoint() {
        if ("hold_place".equals(kind)) {
            return "/v2/holds";
        }
        if ("hold_release".equals(kind)) {
            return "/v2/releases";
        }
        return "/v2/notes";
    }
}
