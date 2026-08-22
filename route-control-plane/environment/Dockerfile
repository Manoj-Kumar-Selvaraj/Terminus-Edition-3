FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY . .

# Materialize the approved starter defect topology. These mutations are applied
# only while building the inherited runtime; the reference repair restores the
# affected production functions from their documented contracts.
RUN sed -i \
      -e 's/return prefix.Masked().String(), nil/return prefix.String(), nil/' \
      internal/controlplane/domain.go \
    && sed -i '/func routeIdentity/,/func ruleIdentity/{/        strconvI(route.Table),/d;}' internal/controlplane/domain.go \
    && sed -i '/func (c \*ControlPlane) Apply/,/func (c \*ControlPlane) Rollback/{s/if existing, ok := c.idempotency\[req.IdempotencyKey\]; ok {/if existing, ok := c.idempotency[req.IdempotencyKey]; ok \&\& false {/;s/if req.BaseRevision != c.desired.Revision {/if false \&\& req.BaseRevision != c.desired.Revision {/;s/if !node.Online {/if false \&\& !node.Online {/;}' internal/controlplane/controlplane.go \
    && sed -i '/func validateDesired/,/func (c \*ControlPlane) managementSafety/{s/if _, ok := nodes\[route.NodeID\]; !ok {/if false {\/\/ starter defect: route node dependency unchecked; _ = nodes[route.NodeID]; if false {/;s/if _, ok := nodes\[rule.NodeID\]; !ok {/if false {\/\/ starter defect: rule node dependency unchecked; _ = nodes[rule.NodeID]; if false {/;s/if other, ok := priorities\[key\]; ok {/if other, ok := priorities[key]; ok \&\& false {/;s/if rule.Action == "lookup" \&\& !tables\[rule.NodeID+"|"+strconvI(rule.Table)\] {/if false \&\& rule.Action == "lookup" \&\& !tables[rule.NodeID+"|"+strconvI(rule.Table)] {/;}' internal/controlplane/controlplane.go \
    && sed -i 's/if item.Kind == DriftUnexpected && !item.Owned { continue }/if false \&\& item.Kind == DriftUnexpected \&\& !item.Owned { continue }/' internal/controlplane/drift.go \
    && sed -i \
      -e 's/if req.WaveSize > c.cfg.MaxWave {/if false \&\& req.WaveSize > c.cfg.MaxWave {/' \
      -e 's/if !selectedSet\[id\] {/if false \&\& !selectedSet[id] {/' \
      -e 's/if observed.Revision==req.Revision {/if false \&\& observed.Revision==req.Revision {/' \
      internal/controlplane/rollout.go \
    && gofmt -w ./cmd ./internal \
    && go build -o /out/routecp ./cmd/routecp

FROM golang:1.24-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -r -m -d /home/routecp -u 10001 routecp \
    && mkdir -p /app/routecp/state /app/routecp/config \
    && chown -R routecp:routecp /app/routecp /home/routecp
COPY --from=build --chown=routecp:routecp /src/ /app/routecp/
COPY --from=build /out/routecp /usr/local/bin/routecp
USER routecp
WORKDIR /app/routecp
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/routecp"]
