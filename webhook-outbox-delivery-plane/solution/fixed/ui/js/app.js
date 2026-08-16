(function () {
  const errBox = () => document.getElementById("error-box");
  function showError(msg) {
    const el = errBox();
    if (el) el.textContent = msg || "";
  }
  async function api(method, path, body, token) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (token) opts.headers["Authorization"] = "Bearer " + token;
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const text = await res.text();
    let data = null;
    try { data = JSON.parse(text); } catch (_) {}
    if (!res.ok) {
      const msg = (data && data.error) ? data.error : text;
      showError(msg);
    } else {
      showError("");
    }
    return { res, data, text };
  }

  window.outboxUI = {
    async enqueue(endpointId, payloadText, idem) {
      let payload = {};
      try { payload = JSON.parse(payloadText || "{}"); } catch (_) { payload = {}; }
      const body = { payload };
      if (idem) body.idempotency_key = idem;
      return api("POST", "/api/v1/endpoints/" + endpointId + "/events", body);
    },
    async claim(eventId, owner, seconds) {
      return api("POST", "/api/v1/events/" + eventId + "/claim", {
        lease_owner: owner,
        lease_seconds: Number(seconds || 30)
      });
    },
    async replay(eventId, token) {
      return api("POST", "/api/v1/events/" + eventId + "/replay", {}, token);
    },
    async pause(endpointId) {
      return api("POST", "/api/v1/endpoints/" + endpointId + "/pause", {});
    },
    async loadAudit() {
      return api("GET", "/api/v1/audit?limit=30");
    }
  };

  function bind() {
    const form = document.getElementById("claim-form");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const eventId = document.getElementById("claim-event").value;
      const owner = document.getElementById("claim-owner").value;
      const seconds = document.getElementById("claim-seconds").value;
      await window.outboxUI.claim(eventId, owner, seconds);
    });
    const replayForm = document.getElementById("replay-form");
    if (replayForm) {
      replayForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const eventId = document.getElementById("replay-event").value;
        const token = document.getElementById("replay-token").value;
        await window.outboxUI.replay(eventId, token);
      });
    }
  }
  document.addEventListener("DOMContentLoaded", bind);
})();
