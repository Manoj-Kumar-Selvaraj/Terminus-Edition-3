#!/usr/bin/env python3
"""Apply reference fixes for sovereign-l4-load-balancer without touching verifier tests."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing patch anchor for {label}")
    return text.replace(old, new, 1)


def patch_control_go(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """\tbody := map[string]any{}
\tencoded, err := json.Marshal(compiled.Snapshot)
\tif err != nil { return }
\tvar snapshotBody any
\tif json.Unmarshal(encoded, &snapshotBody) != nil { return }
\tbody["snapshot"] = snapshotBody"""
    new = """\tbody := map[string]any{"snapshot_canonical": string(compiled.Canonical)}
\tvar snapshotBody any
\tif json.Unmarshal(compiled.Canonical, &snapshotBody) != nil { return }
\tbody["snapshot"] = snapshotBody"""
    text = replace_once(text, old, new, "dispatchPrepare canonical body")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_revision_store(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'type state struct { AcceptedRevision uint64 `json:"accepted_revision"`; NextGeneration uint64 `json:"next_generation"`; Records map[string]Record `json:"records"` }',
        'type state struct { AcceptedRevision uint64 `json:"accepted_revision"`; AcceptedDigest string `json:"accepted_digest"`; NextGeneration uint64 `json:"next_generation"`; Records map[string]Record `json:"records"` }',
        "revision accepted digest field",
    )
    text = replace_once(
        text,
        "\tif revision <= store.state.AcceptedRevision { return 0, nil, ErrStale }",
        "\tif revision < store.state.AcceptedRevision { return 0, nil, ErrStale }\n\tif revision == store.state.AcceptedRevision && store.state.AcceptedDigest != \"\" && requestDigest != store.state.AcceptedDigest { return 0, nil, ErrConflict }",
        "revision digest conflict",
    )
    text = replace_once(
        text,
        "\tnext.AcceptedRevision = revision",
        "\tnext.AcceptedRevision = revision\n\tnext.AcceptedDigest = requestDigest",
        "revision commit digest",
    )
    text = replace_once(
        text,
        "\tif existing, ok := store.state.Records[key]; ok {\n\t\tcopy := existing; return existing.Generation, &copy, nil\n\t}",
        "\tif existing, ok := store.state.Records[key]; ok {\n\t\tif existing.RequestDigest != requestDigest { return 0, nil, ErrConflict }\n\t\tcopy := existing; return existing.Generation, &copy, nil\n\t}",
        "idempotency body fence",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_rollout(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'func count(values map[string]model.NodeResponse, state string) int { total := 0; for _, value := range values { if value.State == state { total++ } }; return total }',
        'func count(values map[string]model.NodeResponse, state string, registry *nodes.Registry) int { total := 0; for nodeID, value := range values { if value.State != state { continue }; if registry.Current(nodeID, value.SessionID) { total++ } }; return total }',
        "rollout connected quorum count",
    )
    text = replace_once(
        text,
        'if count(rollout.NodeResponses, "active") >= 1 && rollout.ActivateQuorum > 0 { rollout.Phase = "active"; coordinator.active = rollout.Generation }',
        'if count(rollout.NodeResponses, "active", coordinator.registry) >= rollout.ActivateQuorum { rollout.Phase = "active"; coordinator.active = rollout.Generation }',
        "rollout activate quorum threshold",
    )
    text = text.replace('count(rollout.NodeResponses, "prepared")', 'count(rollout.NodeResponses, "prepared", coordinator.registry)')
    if 'count(rollout.NodeResponses, "prepared", coordinator.registry)' not in text:
        raise SystemExit("rollout prepare count patch failed")
    text = replace_once(
        text,
        '\t\trollout.NodeResponses[envelope.NodeID] = response(envelope, "rejected")\n\t\trollout.Phase = "rejected"\n\t\treturn clone(*rollout), nil',
        '\t\trollout.NodeResponses[envelope.NodeID] = response(envelope, "rejected")\n\t\trollout.Phase = "rejected"\n\t\tcoordinator.current = nil\n\t\treturn clone(*rollout), nil',
        "rollout reject preserves active",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_service_ready(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = 'func (service *Service) handleReady(writer http.ResponseWriter, _ *http.Request) { _, err := service.repository.Current(); ready := err == nil || service.revisions.AcceptedRevision() == 0; status := http.StatusOK; if !ready { status = http.StatusServiceUnavailable }; writeJSON(writer, status, map[string]bool{"ready":ready}) }'
    new = """func (service *Service) handleReady(writer http.ResponseWriter, _ *http.Request) {
\tready := false
\tif service.revisions.AcceptedRevision() == 0 {
\t\t_, err := service.repository.Current()
\t\tready = err == nil
\t} else if state, ok := service.rollout.Snapshot(); ok {
\t\tswitch state.Phase {
\t\tcase "active":
\t\t\tservice.mutex.RLock()
\t\t\tready = service.active == state.Generation
\t\t\tservice.mutex.RUnlock()
\t\tdefault:
\t\t\tready = false
\t\t}
\t} else {
\t\tservice.mutex.RLock()
\t\tactive := service.active
\t\tservice.mutex.RUnlock()
\t\tif active > 0 {
\t\t\tif current, err := service.repository.Load(active); err == nil {
\t\t\t\tready = len(current.Snapshot.Listeners) > 0
\t\t\t}
\t\t}
\t}
\tstatus := http.StatusOK
\tif !ready {
\t\tstatus = http.StatusServiceUnavailable
\t}
\twriteJSON(writer, status, map[string]bool{"ready": ready})
}"""
    text = replace_once(text, old, new, "readiness gate")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_control_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'static std::string timestamp(){auto value=std::chrono::system_clock::now().time_since_epoch();return std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(value).count());}',
        'static std::string timestamp(){auto value=std::chrono::system_clock::now().time_since_epoch();auto seconds=std::chrono::duration_cast<std::chrono::seconds>(value);auto nanos=std::chrono::duration_cast<std::chrono::nanoseconds>(value-seconds).count();std::time_t now=std::chrono::system_clock::to_time_t(std::chrono::system_clock::time_point(seconds));std::tm tm{};gmtime_r(&now,&tm);char buffer[64];std::snprintf(buffer,sizeof(buffer),"%04d-%02d-%02dT%02d:%02d:%02d",tm.tm_year+1900,tm.tm_mon+1,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);return std::string(buffer)+"."+std::to_string(nanos)+"Z";}',
        "control timestamp format",
    )
    old_prepare = 'const Json& source=request.body.at("snapshot");std::string canonical=write_json(source);if(sha256_hex(canonical)!=request.digest)throw JsonError("snapshot digest mismatch");'
    new_prepare = 'const Json& source=request.body.at("snapshot");std::string canonical=request.body.contains("snapshot_canonical")?request.body.at("snapshot_canonical").string():write_json(source);if(sha256_hex(canonical)!=request.digest)throw JsonError("snapshot digest mismatch");'
    text = replace_once(text, old_prepare, new_prepare, "prepare canonical digest")
    old_activate = 'if(!runtimes_.activate(request.generation,request.digest))throw JsonError("candidate was not prepared");proxy_.publish();'
    new_activate = 'auto previous=runtimes_.active();if(!runtimes_.activate(request.generation,request.digest))throw JsonError("candidate was not prepared");drains_.transition(previous,runtimes_.active(),std::chrono::steady_clock::now());proxy_.publish();'
    text = replace_once(text, old_activate, new_activate, "activate drain transition")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_eligibility(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """std::vector<const Target*> Eligibility::eligible(const TargetGroup& group,const std::string& local_zone,std::chrono::steady_clock::time_point now)const{std::vector<const Target*> local,remote;for(const auto& target:group.targets){if(!normally_eligible(target,now))continue;(target.zone==local_zone?local:remote).push_back(&target);}if(group.zone_policy==ZonePolicy::cross_zone){local.insert(local.end(),remote.begin(),remote.end());return local;}if(!local.empty())return local;if(!remote.empty())return remote;if(!group.fail_open)return{};for(const auto& target:group.targets){if(target.administrative==AdminState::draining&&state(target.identity).drain_deadline>now)continue;(target.zone==local_zone?local:remote).push_back(&target);}if(!local.empty())return local;return remote;}"""
    new = """std::vector<const Target*> Eligibility::eligible(const TargetGroup& group,const std::string& local_zone,std::chrono::steady_clock::time_point now)const{std::vector<const Target*> local,remote;for(const auto& target:group.targets){if(!normally_eligible(target,now))continue;(target.zone==local_zone?local:remote).push_back(&target);}if(group.zone_policy==ZonePolicy::cross_zone){local.insert(local.end(),remote.begin(),remote.end());return local;}if(!local.empty())return local;if(group.fail_open){local.clear();remote.clear();for(const auto& target:group.targets){if(target.administrative==AdminState::disabled)continue;const auto& runtime=state(target.identity);if(runtime.drain_deadline>now)continue;(target.zone==local_zone?local:remote).push_back(&target);}if(!local.empty())return local;return remote;}return{};}"""
    text = replace_once(text, old, new, "eligibility zone fail-open")
    text = replace_once(
        text,
        'bool Eligibility::fail_open_eligible(const Target& target,std::chrono::steady_clock::time_point now)const{const auto& runtime=state(target.identity);return target.administrative==AdminState::enabled&&runtime.drain_deadline<=now;}',
        'bool Eligibility::fail_open_eligible(const Target& target,std::chrono::steady_clock::time_point now)const{const auto& runtime=state(target.identity);return target.administrative!=AdminState::disabled&&runtime.drain_deadline<=now;}',
        "fail-open disabled filter",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_proxy(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'if((events&EPOLLIN)&&!transfer_read(descriptor,connection->target_to_client,connection->target_read_closed)){close_connection(connection);return;}',
        'if((events&EPOLLIN)&&!transfer_read(descriptor,connection->target_to_client,connection->target_read_closed)){health_.passive_failure(*connection->target,connection->snapshot->group(connection->listener->target_group).health,std::chrono::steady_clock::now());close_connection(connection);return;}',
        "passive failure on target read error",
    )
    # inject HealthTracker reference - proxy needs health_ member. Check proxy.hpp
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_proxy_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "HealthTracker& health_" not in text:
        raise SystemExit("proxy.hpp must declare HealthTracker before passive patch")


def patch_selector(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'if(group.policy==BalancePolicy::source_hash)return candidates[stable_hash(source)%candidates.size()];',
        'if(group.policy==BalancePolicy::source_hash)return candidates[stable_hash(source+"\\0"+group.name)%candidates.size()];',
        "source hash group salt",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_metrics(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '\tservice.metrics.Inc("sovereign_apply_total", fmt.Sprintf("generation=%d", generation))',
        '\tservice.metrics.Inc("sovereign_apply_total", "result=accepted")',
        "bounded metric labels",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_expire(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = '(now>idle_limit&&connection->client_to_target.readable()==0&&connection->target_to_client.readable()==0)'
    new = '(now>idle_limit&&connection->client_to_target.readable()==0&&connection->target_to_client.readable()==0&&connection->client_to_target.writable()==connection->listener->buffer_bytes&&connection->target_to_client.writable()==connection->listener->buffer_bytes)'
    text = replace_once(text, old, new, "idle timeout buffered bytes")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_checkpoint(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    padded = 'char padded[64];std::snprintf(padded,sizeof(padded),"generation-%020llu",static_cast<unsigned long long>(generation));auto directory=root_/padded;'
    text = text.replace('auto directory=root_/("generation-"+std::to_string(generation));', padded)
    if padded not in text:
        raise SystemExit("checkpoint generation padding patch failed")
    text = text.replace('name.rfind("generation-",0)!=0)continue;auto value=std::stoull(name.substr(11));', 'name.rfind("generation-",0)!=0)continue;auto value=std::stoull(name.substr(11));')
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_protocol(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = 'while (buffer_.size() >= 4) { std::uint32_t network{}; std::memcpy(&network,buffer_.data(),4); std::uint32_t length=ntohl(network); if(length==0||length>maximum_) throw JsonError("invalid frame length"); if(buffer_.size()<4+length) break; frames.emplace_back(reinterpret_cast<const char*>(buffer_.data()+4),length); buffer_.erase(buffer_.begin(),buffer_.begin()+4+length); }'
    new = 'while (buffer_.size() >= 4) { std::uint32_t network{}; std::memcpy(&network,buffer_.data(),4); std::uint32_t length=ntohl(network); if(length==0||length>maximum_) { buffer_.clear(); throw JsonError("invalid frame length"); } if(buffer_.size()<4+length) break; frames.emplace_back(reinterpret_cast<const char*>(buffer_.data()+4),length); buffer_.erase(buffer_.begin(),buffer_.begin()+4+length); }'
    text = replace_once(text, old, new, "torn frame guard")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_proxy_hpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "HealthTracker" in text:
        return
    text = replace_once(text, '#include "sovereign/connection.hpp"', '#include "sovereign/connection.hpp"\n#include "sovereign/health.hpp"', "proxy health include")
    text = replace_once(
        text,
        'Proxy(RuntimeStore& runtimes,Eligibility& eligibility,std::string zone,std::size_t maximum_connections);',
        'Proxy(RuntimeStore& runtimes,Eligibility& eligibility,HealthTracker& health,std::string zone,std::size_t maximum_connections);',
        "proxy health ctor",
    )
    text = replace_once(text, 'RuntimeStore& runtimes_;Eligibility& eligibility_;Selector selector_;', 'RuntimeStore& runtimes_;Eligibility& eligibility_;HealthTracker& health_;Selector selector_;', "proxy health member")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_proxy_cpp_ctor(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'Proxy::Proxy(RuntimeStore& runtimes,Eligibility& eligibility,std::string zone,std::size_t maximum_connections):runtimes_(runtimes),eligibility_(eligibility),zone_(std::move(zone)),connections_(maximum_connections){',
        'Proxy::Proxy(RuntimeStore& runtimes,Eligibility& eligibility,HealthTracker& health,std::string zone,std::size_t maximum_connections):runtimes_(runtimes),eligibility_(eligibility),health_(health),zone_(std::move(zone)),connections_(maximum_connections){',
        "proxy ctor health",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_main_cpp(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'sovereign::Proxy proxy(runtimes,eligibility,config.zone,config.max_connections);',
        'sovereign::Proxy proxy(runtimes,eligibility,health,config.zone,config.max_connections);',
        "main proxy ctor",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} SOVEREIGN_LB_ROOT", file=sys.stderr)
        return 2
    root = Path(argv[1])
    patch_control_go(root / "internal/api/control.go")
    patch_revision_store(root / "internal/revision/store.go")
    patch_rollout(root / "internal/rollout/coordinator.go")
    patch_service_ready(root / "internal/api/service.go")
    patch_control_cpp(root / "dataplane/src/control.cpp")
    patch_eligibility(root / "dataplane/src/eligibility.cpp")
    patch_proxy_hpp(root / "dataplane/include/sovereign/proxy.hpp")
    patch_proxy_cpp_ctor(root / "dataplane/src/proxy.cpp")
    patch_proxy(root / "dataplane/src/proxy.cpp")
    patch_expire(root / "dataplane/src/proxy.cpp")
    patch_selector(root / "dataplane/src/selector.cpp")
    patch_metrics(root / "internal/api/service.go")
    patch_checkpoint(root / "dataplane/src/checkpoint.cpp")
    patch_protocol(root / "dataplane/src/protocol.cpp")
    patch_main_cpp(root / "dataplane/src/main.cpp")
    print("repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
