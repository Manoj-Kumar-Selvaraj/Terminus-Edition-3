type NodeRecord = {
  id: string;
  hostname: string;
  site: string;
  environment: string;
  management_ip: string;
  online: boolean;
  heartbeat_revision: number;
  labels: Record<string, string>;
};

type RouteRecord = {
  id: string;
  node_id: string;
  family: string;
  destination: string;
  table: number;
  metric: number;
  owner: string;
  next_hops: Array<{gateway: string; interface: string; weight: number}>;
};

type DriftItem = {
  node_id: string;
  kind: "missing" | "unexpected" | "changed";
  object_type: string;
  object_id: string;
  owned: boolean;
};

type Snapshot = {
  desired: {revision: number; routes: RouteRecord[]};
  nodes: Record<string, NodeRecord>;
};

class RouteCPApi {
  constructor(private readonly base = "") {}

  async state(): Promise<Snapshot> {
    return this.get<Snapshot>("/v1/state");
  }

  async nodes(): Promise<NodeRecord[]> {
    return this.get<NodeRecord[]>("/v1/nodes");
  }

  async routes(node = ""): Promise<RouteRecord[]> {
    const query = node ? `?node=${encodeURIComponent(node)}` : "";
    return this.get<RouteRecord[]>(`/v1/routes${query}`);
  }

  async drift(node = ""): Promise<DriftItem[]> {
    const query = node ? `?node=${encodeURIComponent(node)}` : "";
    return this.get<DriftItem[]>(`/v1/drift${query}`);
  }

  async preview(input: unknown): Promise<unknown> {
    return this.post("/v1/revisions/preview", input);
  }

  async apply(input: unknown): Promise<unknown> {
    return this.post("/v1/revisions/apply", input);
  }

  async reconcile(input: unknown): Promise<unknown> {
    return this.post("/v1/reconcile", input);
  }

  async rollout(input: unknown): Promise<unknown> {
    return this.post("/v1/rollouts", input);
  }

  private async get<T>(path: string): Promise<T> {
    const response = await fetch(this.base + path, {headers: {Accept: "application/json"}});
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<T>;
  }

  private async post<T>(path: string, body: T): Promise<unknown> {
    const response = await fetch(this.base + path, {
      method: "POST",
      headers: {"Content-Type": "application/json", Accept: "application/json"},
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
}

class Dashboard {
  private readonly api = new RouteCPApi();
  private revision = 0;
  private selectedNode = "";

  async start(): Promise<void> {
    this.bind();
    await this.refresh();
    window.setInterval(() => void this.refresh(), 15000);
  }

  private bind(): void {
    document.querySelector<HTMLButtonElement>("#refresh")?.addEventListener("click", () => void this.refresh());
    document.querySelector<HTMLSelectElement>("#node")?.addEventListener("change", (event) => {
      this.selectedNode = (event.currentTarget as HTMLSelectElement).value;
      void this.refreshNode();
    });
    document.querySelector<HTMLFormElement>("#route-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.submitRoute(event.currentTarget as HTMLFormElement);
    });
    document.querySelector<HTMLButtonElement>("#reconcile")?.addEventListener("click", () => void this.reconcile());
    document.querySelector<HTMLButtonElement>("#rollout")?.addEventListener("click", () => void this.rollout());
  }

  private async refresh(): Promise<void> {
    try {
      const [state, nodes] = await Promise.all([this.api.state(), this.api.nodes()]);
      this.revision = state.desired.revision;
      this.renderRevision();
      this.renderNodes(nodes);
      await this.refreshNode();
      this.setStatus("ready");
    } catch (error) {
      this.setStatus(String(error));
    }
  }

  private async refreshNode(): Promise<void> {
    const [routes, drift] = await Promise.all([
      this.api.routes(this.selectedNode),
      this.api.drift(this.selectedNode),
    ]);
    this.renderRoutes(routes);
    this.renderDrift(drift);
  }

  private renderRevision(): void {
    const element = document.querySelector<HTMLElement>("#revision");
    if (element) element.textContent = String(this.revision);
  }

  private renderNodes(nodes: NodeRecord[]): void {
    const selector = document.querySelector<HTMLSelectElement>("#node");
    if (!selector) return;
    const previous = this.selectedNode;
    selector.replaceChildren(new Option("All nodes", ""));
    for (const node of nodes) {
      const status = node.online ? "online" : "offline";
      selector.add(new Option(`${node.id} · ${node.site} · ${status}`, node.id));
    }
    selector.value = previous;
  }

  private renderRoutes(routes: RouteRecord[]): void {
    const body = document.querySelector<HTMLTableSectionElement>("#routes tbody");
    if (!body) return;
    body.replaceChildren();
    for (const route of routes) {
      const row = body.insertRow();
      row.insertCell().textContent = route.node_id;
      row.insertCell().textContent = route.destination;
      row.insertCell().textContent = String(route.table);
      row.insertCell().textContent = String(route.metric);
      row.insertCell().textContent = route.next_hops.map((hop) => `${hop.gateway}%${hop.interface}(${hop.weight})`).join(", ");
      row.insertCell().textContent = route.owner;
    }
  }

  private renderDrift(items: DriftItem[]): void {
    const body = document.querySelector<HTMLTableSectionElement>("#drift tbody");
    if (!body) return;
    body.replaceChildren();
    for (const item of items) {
      const row = body.insertRow();
      row.insertCell().textContent = item.node_id;
      row.insertCell().textContent = item.kind;
      row.insertCell().textContent = item.object_type;
      row.insertCell().textContent = item.object_id;
      row.insertCell().textContent = item.owned ? "managed" : "external";
    }
  }

  private async submitRoute(form: HTMLFormElement): Promise<void> {
    const data = new FormData(form);
    const node = String(data.get("node") ?? "");
    const destination = String(data.get("destination") ?? "");
    const gateway = String(data.get("gateway") ?? "");
    const iface = String(data.get("interface") ?? "eth0");
    const table = Number(data.get("table") ?? 254);
    const metric = Number(data.get("metric") ?? 100);
    try {
      const plan = await this.api.preview({
        base_revision: this.revision,
        actor: "dashboard",
        reason: "operator route change",
        route_mutations: [{
          operation: "add",
          route: {
            id: `ui-${node}-${destination}-${table}-${metric}`,
            node_id: node,
            destination,
            table,
            metric,
            protocol: "static",
            scope: "global",
            type: "unicast",
            owner: "routecp",
            next_hops: [{gateway, interface: iface, weight: 1}],
          },
        }],
        rule_mutations: [],
      }) as {id: string};
      await this.api.apply({
        plan_id: plan.id,
        base_revision: this.revision,
        idempotency_key: crypto.randomUUID(),
        nodes: [node],
        actor: "dashboard",
      });
      await this.refresh();
    } catch (error) {
      this.setStatus(`route mutation failed: ${String(error)}`);
    }
  }

  private async reconcile(): Promise<void> {
    if (!this.selectedNode) {
      this.setStatus("choose one node before reconciling");
      return;
    }
    try {
      await this.api.reconcile({node_id: this.selectedNode, actor: "dashboard", dry_run: false});
      await this.refresh();
    } catch (error) {
      this.setStatus(`reconcile failed: ${String(error)}`);
    }
  }

  private async rollout(): Promise<void> {
    try {
      await this.api.rollout({
        revision: this.revision,
        selector: {role: "edge"},
        wave_size: 10,
        canary_nodes: [],
        actor: "dashboard",
      });
      await this.refresh();
    } catch (error) {
      this.setStatus(`rollout failed: ${String(error)}`);
    }
  }

  private setStatus(message: string): void {
    const element = document.querySelector<HTMLElement>("#status");
    if (element) element.textContent = message;
  }
}

void new Dashboard().start();
