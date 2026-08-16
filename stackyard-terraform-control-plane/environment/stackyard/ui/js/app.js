const state = {
  orgId: null,
  workspaceId: null,
  runId: null,
  token: localStorage.getItem("STACKYARD_TOKEN") || "",
};

function headers() {
  const h = { "Content-Type": "application/json" };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { ...headers(), ...(opts.headers || {}) },
  });
  const text = await res.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text }; }
  if (!res.ok) {
    return body;
  }
  document.getElementById("error-box").textContent = "";
  return body;
}

function showError() {
}

async function refreshOrgs() {
  const data = await api("/api/v1/orgs");
  const list = document.getElementById("org-list");
  list.innerHTML = "";
  (data.orgs || []).forEach((o) => {
    const li = document.createElement("li");
    li.textContent = `${o.name} (${o.slug})`;
    li.onclick = () => {
      state.orgId = o.id;
      document.getElementById("selected-org").textContent = o.id;
      refreshWorkspaces();
    };
    list.appendChild(li);
  });
}

async function refreshWorkspaces() {
  if (!state.orgId) return;
  const data = await api(`/api/v1/orgs/${state.orgId}/workspaces`);
  const list = document.getElementById("ws-list");
  list.innerHTML = "";
  (data.workspaces || []).forEach((ws) => {
    const li = document.createElement("li");
    li.textContent = `${ws.name} locked=${ws.locked}`;
    li.onclick = () => {
      state.workspaceId = ws.id;
      document.getElementById("selected-ws").textContent = ws.id;
      refreshVars();
      refreshRuns();
      refreshLock();
    };
    list.appendChild(li);
  });
}

async function refreshVars() {
  if (!state.workspaceId) return;
  const data = await api(`/api/v1/workspaces/${state.workspaceId}/vars`);
  const list = document.getElementById("var-list");
  list.innerHTML = "";
  (data.vars || []).forEach((v) => {
    const li = document.createElement("li");
    li.textContent = `${v.key}=${v.value} (${v.category}${v.sensitive ? ", sensitive" : ""})`;
    list.appendChild(li);
  });
}

async function refreshRuns() {
  if (!state.workspaceId) return;
  const data = await api(`/api/v1/workspaces/${state.workspaceId}/runs`);
  const list = document.getElementById("run-list");
  list.innerHTML = "";
  (data.runs || []).forEach((run) => {
    const li = document.createElement("li");
    li.textContent = `${run.id} ${run.command} ${run.status}`;
    li.onclick = () => {
      state.runId = run.id;
      [...list.children].forEach((c) => c.classList.remove("selected"));
      li.classList.add("selected");
    };
    list.appendChild(li);
  });
}

async function refreshLock() {
  if (!state.workspaceId) return;
  const res = await fetch(`/api/v1/workspaces/${state.workspaceId}/lock`, { headers: headers() });
  const box = document.getElementById("lock-view");
  if (res.status === 404) {
    box.textContent = "unlocked";
    return;
  }
  box.textContent = await res.text();
}

document.getElementById("refresh-orgs").onclick = refreshOrgs;

document.getElementById("ws-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.orgId) return;
  const fd = new FormData(e.target);
  await api(`/api/v1/orgs/${state.orgId}/workspaces`, {
    method: "POST",
    body: JSON.stringify({
      name: fd.get("name"),
      working_directory: fd.get("working_directory"),
    }),
  });
  refreshWorkspaces();
};

document.getElementById("var-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.workspaceId) return;
  const fd = new FormData(e.target);
  await api(`/api/v1/workspaces/${state.workspaceId}/vars`, {
    method: "POST",
    body: JSON.stringify({
      key: fd.get("key"),
      value: fd.get("value"),
      category: fd.get("category"),
      sensitive: fd.get("sensitive") === "on",
    }),
  });
  refreshVars();
};

document.getElementById("lock-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.workspaceId) return;
  const fd = new FormData(e.target);
  await api(`/api/v1/workspaces/${state.workspaceId}/lock`, {
    method: "POST",
    body: JSON.stringify({ holder: fd.get("holder"), reason: fd.get("reason") }),
  });
  refreshLock();
  refreshWorkspaces();
};

document.getElementById("unlock-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.workspaceId) return;
  const fd = new FormData(e.target);
  await api(`/api/v1/workspaces/${state.workspaceId}/unlock`, {
    method: "POST",
    body: JSON.stringify({ holder: fd.get("holder") }),
  });
  refreshLock();
  refreshWorkspaces();
};

document.getElementById("run-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.workspaceId) return;
  const fd = new FormData(e.target);
  await api(`/api/v1/workspaces/${state.workspaceId}/runs`, {
    method: "POST",
    body: JSON.stringify({
      cmd: fd.get("command"),
      message: fd.get("message") || "",
    }),
  });
  refreshRuns();
};

document.getElementById("discard-run").onclick = async () => {
  if (!state.runId) return;
  await api(`/api/v1/runs/${state.runId}/discard`, { method: "POST", body: "{}" });
  refreshRuns();
};

document.getElementById("cancel-run").onclick = async () => {
  if (!state.runId) return;
  await api(`/api/v1/runs/${state.runId}/cancel`, { method: "POST", body: "{}" });
  refreshRuns();
};

refreshOrgs();
