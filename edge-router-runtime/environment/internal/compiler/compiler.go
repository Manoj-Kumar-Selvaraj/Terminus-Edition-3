package compiler

import (
	"fmt"
	"sort"
	"strings"

	rt "edge-router/internal/runtime"
)

type Compiler struct {
	registry *rt.Registry
}

func New(registry *rt.Registry) *Compiler {
	return &Compiler{registry: registry}
}

func (c *Compiler) Compile(state rt.DesiredState, generation uint64) (*rt.RuntimeSnapshot, error) {
	if generation == 0 {
		return nil, fmt.Errorf("generation must be positive")
	}
	routes, err := c.compileRoutes(state.Routes)
	if err != nil {
		return nil, err
	}
	pools, err := c.compilePools(state.Pools)
	if err != nil {
		return nil, err
	}
	for _, route := range routes {
		if pools[route.PoolID] == nil {
			return nil, fmt.Errorf("route %s references unknown pool %s", route.ID, route.PoolID)
		}
	}
	return &rt.RuntimeSnapshot{
		Generation: generation,
		Routes: routes,
		Pools: pools,
		Desired: state,
		SourceRevisions: rt.CloneRevisions(state.SourceRevisions),
		SourceDigests: rt.CloneDigests(state.SourceDigests),
		State: rt.SnapshotBuilding,
	}, nil
}

func (c *Compiler) compileRoutes(specs []rt.RouteSpec) ([]rt.CompiledRoute, error) {
	compiled := make([]rt.CompiledRoute, 0, len(specs))
	for _, spec := range specs {
		methods := make(map[string]struct{}, len(spec.Match.Methods))
		for _, method := range spec.Match.Methods {
			method = strings.ToUpper(strings.TrimSpace(method))
			if method != "" {
				methods[method] = struct{}{}
			}
		semantic := struct {
			ID string
			Host string
			Path string
			Methods []string
			PoolID string
			Priority int
		}{
			ID: spec.ID,
			Host: strings.ToLower(spec.Match.Host),
			Path: spec.Match.PathPrefix,
			Methods: sortedMethods(methods),
			PoolID: spec.PoolID,
			Priority: spec.Priority,
		}
		compiled = append(compiled, rt.CompiledRoute{
			ID: spec.ID,
			Host: semantic.Host,
			PathPrefix: semantic.Path,
			Methods: methods,
			PoolID: spec.PoolID,
			Priority: spec.Priority,
			SemanticDigest: rt.SemanticDigest(semantic),
		})
	}
	sort.SliceStable(compiled, func(i, j int) bool {
		if compiled[i].Priority != compiled[j].Priority {
			return compiled[i].Priority > compiled[j].Priority
		}
		if len(compiled[i].PathPrefix) != len(compiled[j].PathPrefix) {
			return len(compiled[i].PathPrefix) > len(compiled[j].PathPrefix)
		}
		return compiled[i].ID < compiled[j].ID
	})
	return compiled, nil
}

func (c *Compiler) compilePools(specs []rt.PoolSpec) (map[string]*rt.PoolView, error) {
	out := make(map[string]*rt.PoolView, len(specs))
	for _, spec := range specs {
		if spec.ID == "" {
			return nil, fmt.Errorf("pool id is required")
		}
		compatibility := poolCompatibility(spec)
		_ = c.registry.Pool(spec.ID, compatibility)
		view := &rt.PoolView{
			ID: spec.ID,
			Selection: spec.Selection,
			Retry: spec.Retry,
			Failover: append([]string(nil), spec.Failover...),
			Health: spec.Health,
			Drain: spec.Drain,
			Compatibility: compatibility,
		}
		for index, endpoint := range spec.Endpoints {
			identity := endpointIdentity(spec.ID, endpoint, index)
			runtimeHandle := c.registry.Endpoint(spec.ID, identity, endpoint.Address)
			view.Endpoints = append(view.Endpoints, rt.EndpointView{
				Identity: identity,
				Address: endpoint.Address,
				Weight: endpoint.Weight,
				Incarnation: runtimeHandle.Incarnation,
				Runtime: runtimeHandle,
			})
		}
		out[spec.ID] = view
	}
	return out, nil
}

func endpointIdentity(poolID string, endpoint rt.EndpointSpec, declarationIndex int) string {
	transport := endpoint.Transport
	if transport == "" {
		transport = "http"
	}
	return fmt.Sprintf("%s|%s|%s|%d", poolID, endpoint.Address, transport, declarationIndex)
}

func poolCompatibility(spec rt.PoolSpec) string {
	metadata := rt.StableStringMap(spec.Metadata)
	shape := struct {
		ID string
		Mode string
		Metadata [][2]string
	}{
		ID: spec.ID,
		Mode: spec.Selection.Mode,
		Metadata: metadata,
	}
	return rt.SemanticDigest(shape)
}

func sortedMethods(methods map[string]struct{}) []string {
	out := make([]string, 0, len(methods))
	for method := range methods {
		out = append(out, method)
	}
	sort.Strings(out)
	return out
}

func RouteEquivalent(a, b rt.CompiledRoute) bool {
	return a.ID == b.ID && a.SemanticDigest == b.SemanticDigest
}

func PoolEquivalent(a, b *rt.PoolView) bool {
	if a == nil || b == nil {
		return a == b
	}
	if a.ID != b.ID || a.Compatibility != b.Compatibility {
		return false
	}
	if len(a.Endpoints) != len(b.Endpoints) {
		return false
	}
	for index := range a.Endpoints {
		left := a.Endpoints[index]
		right := b.Endpoints[index]
		if left.Identity != right.Identity || left.Weight != right.Weight {
			return false
		}
	}
	return true
}

func SnapshotDigest(snapshot *rt.RuntimeSnapshot) string {
	if snapshot == nil {
		return ""
	}
	type routeDigest struct {
		ID string
		Digest string
	}
	type poolDigest struct {
		ID string
		Compatibility string
		Endpoints []string
	}
	payload := struct {
		Routes []routeDigest
		Pools []poolDigest
	}{}
	for _, route := range snapshot.Routes {
		payload.Routes = append(payload.Routes, routeDigest{ID: route.ID, Digest: route.SemanticDigest})
	}
	poolIDs := make([]string, 0, len(snapshot.Pools))
	for id := range snapshot.Pools {
		poolIDs = append(poolIDs, id)
	}
	sort.Strings(poolIDs)
	for _, id := range poolIDs {
		pool := snapshot.Pools[id]
		item := poolDigest{ID: id, Compatibility: pool.Compatibility}
		for _, endpoint := range pool.Endpoints {
			item.Endpoints = append(item.Endpoints, endpoint.Identity)
		}
		payload.Pools = append(payload.Pools, item)
	}
	return rt.SemanticDigest(payload)
}
