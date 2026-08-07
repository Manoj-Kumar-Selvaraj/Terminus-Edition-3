package main

import (
	"bytes"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

const featureLevel = 5
const schemaVersion = "vpc-reconcile.aws.1"

type Recovery struct {
	Root   string
	Config map[string]any
	CP     string
	client *http.Client
}

type JournalRecord struct {
	Event        string `json:"event"`
	Owner        string `json:"owner,omitempty"`
	ConfigDigest string `json:"config_digest,omitempty"`
	Stage        string `json:"stage,omitempty"`
	StateDigest  string `json:"state_digest,omitempty"`
	Token        string `json:"token,omitempty"`
}

type Observed struct {
	RouteTables []map[string]any `json:"route_tables"`
	Endpoints   []map[string]any `json:"endpoints"`
	NatHealth   map[string]any   `json:"nat_health"`
	Imports     map[string]any   `json:"imports"`
	Audit       map[string]any   `json:"audit"`
}

func main() {
	if len(os.Args) < 2 {
		die("subcommand required")
	}
	cmd := os.Args[1]
	fs := flag.NewFlagSet(cmd, flag.ExitOnError)
	root := fs.String("root", "/app", "incident root")
	jsonOut := fs.Bool("json", false, "json output")
	owner := fs.String("owner", "", "recovery owner")
	failAfter := fs.String("fail-after", "", "failure injection stage")
	_ = fs.Parse(os.Args[2:])
	r, err := LoadRecovery(*root)
	if err != nil {
		failJSON(*jsonOut, err)
		return
	}
	switch cmd {
	case "inspect":
		reachable := r.Health()
		printJSON(map[string]any{"phase": "ROUTING_DRIFT", "feature_level": featureLevel, "controlplane_reachable": reachable})
	case "plan":
		st, err := r.BuildState()
		if err != nil {
			failJSON(*jsonOut, err)
			return
		}
		st["plan_only"] = true
		printJSON(st)
	case "apply":
		if *owner == "" {
			failJSON(*jsonOut, errors.New("owner is required"))
			return
		}
		out, err := r.Apply(*owner, *failAfter)
		if err != nil {
			failJSON(*jsonOut, err)
			return
		}
		printJSON(out)
	case "resume":
		if *owner == "" {
			failJSON(*jsonOut, errors.New("owner is required"))
			return
		}
		out, err := r.Apply(*owner, "")
		if err != nil {
			failJSON(*jsonOut, err)
			return
		}
		out["resumed"] = true
		printJSON(out)
	case "verify":
		st, meta, err := r.LoadState()
		if err != nil {
			failJSON(*jsonOut, err)
			return
		}
		ok := st != nil && str(st["schema_version"]) == schemaVersion
		out := map[string]any{"valid": ok, "phase": map[bool]string{true: "READY", false: "INCOMPLETE"}[ok]}
		if ok {
			out["config_digest"] = st["config_digest"]
			out["state_digest"] = digestMap(st)
			out["outputs"] = st["outputs"]
			out["controlplane_token_route"] = meta["token_route"]
			out["controlplane_token_endpoint"] = meta["token_endpoint"]
		}
		printJSON(out)
	default:
		die("unknown subcommand: " + cmd)
	}
}

func LoadRecovery(root string) (*Recovery, error) {
	cfg, err := readMap(filepath.Join(root, "data", "desired.json"))
	if err != nil {
		return nil, err
	}
	cp := os.Getenv("VPC_CONTROLPLANE_URL")
	if cp == "" {
		cp = "http://127.0.0.1:7432"
	}
	return &Recovery{Root: root, Config: cfg, CP: strings.TrimRight(cp, "/"), client: &http.Client{Timeout: 5 * time.Second}}, nil
}

func (r *Recovery) Health() bool {
	resp, err := r.client.Get(r.CP + "/health")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

func (r *Recovery) FetchObserved() (*Observed, error) {
	resp, err := r.client.Get(r.CP + "/v1/observed")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("controlplane observed: %s", string(b))
	}
	var obs Observed
	if err := json.Unmarshal(b, &obs); err != nil {
		return nil, err
	}
	return &obs, nil
}

func (r *Recovery) postCommit(path string, body map[string]any) (string, error) {
	payload, _ := json.Marshal(body)
	resp, err := r.client.Post(r.CP+path, "application/json", bytes.NewReader(payload))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	if resp.StatusCode >= 300 {
		return "", fmt.Errorf("controlplane commit failed: %s", string(b))
	}
	var out map[string]any
	if err := json.Unmarshal(b, &out); err != nil {
		return "", err
	}
	tok := str(out["token"])
	if tok == "" {
		return "", errors.New("controlplane returned empty token")
	}
	return tok, nil
}

func (r *Recovery) BuildState() (map[string]any, error) {
	obs, err := r.FetchObserved()
	if err != nil {
		return nil, err
	}
	if err := r.ValidateCIDRs(obs); err != nil {
		return nil, err
	}
	if err := r.ValidateNATs(obs); err != nil {
		return nil, err
	}
	if err := r.ValidateEndpoints(obs); err != nil {
		return nil, err
	}
	if err := r.ValidateAudit(obs); err != nil {
		return nil, err
	}
	env := str(r.Config["environment"])
	if env == "" {
		env = "prod"
	}
	imported := r.ImportByCIDR(obs)
	subs := []map[string]any{}
	rts := []map[string]any{}
	for _, s := range maps(r.Config["subnets"]) {
		tier, az, cidr := str(s["tier"]), str(s["az"]), str(s["cidr"])
		sid := id("subnet", env, tier, azSuffix(az))
		rtid := id("rtb", env, tier, azSuffix(az))
		if im, ok := imported[cidr]; ok {
			if str(im["id"]) != "" {
				sid = str(im["id"])
			}
			if str(im["route_table_id"]) != "" {
				rtid = str(im["route_table_id"])
			}
		}
		meta := map[string]any{"source": "desired"}
		obsRT := r.ObservedRoute(obs, tier, az)
		if obsRT != nil {
			if m, ok := obsRT["metadata"].(map[string]any); ok {
				meta = m
			}
			if str(obsRT["id"]) != "" && imported[cidr] == nil {
				rtid = str(obsRT["id"])
			}
		}
		if im, ok := imported[cidr]; ok && str(im["route_table_id"]) != "" {
			rtid = str(im["route_table_id"])
		}
		subnet := map[string]any{
			"id": sid, "name": s["name"], "tier": tier, "az": az, "cidr": cidr, "route_table_id": rtid,
			"address": fmt.Sprintf("module.vpc.aws_subnet.%s[\"%s\"]", tier, az),
			"tags":    map[string]any{"Name": s["name"], "Tier": tier, "AvailabilityZone": az, "Environment": env},
		}
		subs = append(subs, subnet)
		routes := []map[string]any{}
		if tier == "public" {
			routes = append(routes, map[string]any{"destination": "0.0.0.0/0", "target": str(r.Config["internet_gateway_id"]), "owner": "terraform-aws-vpc-module"})
		}
		if tier == "app" {
			routes = append(routes, map[string]any{"destination": "0.0.0.0/0", "target": r.NATForAZ(obs, az), "owner": "terraform-aws-vpc-module"})
		}
		if obsRT != nil {
			for _, or := range maps(obsRT["routes"]) {
				if str(or["owner"]) == "manual" {
					routes = append(routes, or)
				}
			}
		}
		rts = append(rts, map[string]any{
			"id": rtid, "tier": tier, "az": az, "routes": routes, "metadata": meta,
			"tags": map[string]any{"Tier": tier, "AvailabilityZone": az, "ManagedBy": "terraform-aws-vpc-module"},
		})
	}
	outputs := map[string]any{
		"vpc_id":                        id("vpc", env),
		"public_subnet_ids":             ids(subs, "public"),
		"private_app_subnet_ids":        ids(subs, "app"),
		"isolated_data_subnet_ids":      ids(subs, "data"),
		"private_app_route_table_ids":   rtids(rts, "app"),
		"isolated_data_route_table_ids": rtids(rts, "data"),
	}
	actions := []map[string]any{}
	actions = append(actions, r.RouteActions(rts)...)
	endpoints, ea := r.RenderEndpoints(obs, outputs)
	actions = append(actions, ea...)
	moved := r.MovedActions(obs, subs)
	actions = append(actions, moved...)
	flow, resolver, drift := r.RenderAudit(obs, subs, env)
	for _, d := range drift {
		actions = append(actions, d)
	}
	return map[string]any{
		"schema_version": schemaVersion, "environment": env, "config_digest": r.ConfigDigest(),
		"vpc": map[string]any{"id": id("vpc", env), "cidr": r.Config["vpc_cidr"], "tags": map[string]any{"Environment": env, "ManagedBy": "terraform-aws-vpc-module"}},
		"subnets": subs, "route_tables": rts, "gateway_endpoints": endpoints, "flow_log": flow,
		"resolver_security_group": resolver, "outputs": outputs, "moved": moved, "drift_report": drift, "plan_actions": actions,
	}, nil
}

func (r *Recovery) Apply(owner, failAfter string) (map[string]any, error) {
	if err := r.EnsureDB(); err != nil {
		return nil, err
	}
	if err := r.RepairJournal(); err != nil {
		return nil, err
	}
	st, err := r.BuildState()
	if err != nil {
		return nil, err
	}
	if err := r.CheckOwner(owner); err != nil {
		return nil, err
	}
	if failAfter == "" && r.AlreadyCommitted(owner) {
		return map[string]any{"applied": true, "owner": owner, "config_digest": r.ConfigDigest(), "idempotent": true}, nil
	}
	if err := r.AppendJournal(JournalRecord{Event: "route_plan_written", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "route"}); err != nil {
		return nil, err
	}
	tokRoute, err := r.postCommit("/v1/routes/commit", map[string]any{
		"owner": owner, "config_digest": r.ConfigDigest(), "route_tables": st["route_tables"],
	})
	if err != nil {
		return nil, err
	}
	_ = r.SetMeta("token_route", tokRoute)
	_ = r.AppendJournal(JournalRecord{Event: "route_commit", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "route", Token: tokRoute})
	if err := r.WriteState(st); err != nil {
		return nil, err
	}
	if failAfter == "route_commit" {
		_ = r.AppendJournal(JournalRecord{Event: "route_commit_lost", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "route", Token: tokRoute})
		return nil, errors.New("injected failure after route_commit")
	}
	if err := r.AppendJournal(JournalRecord{Event: "endpoint_plan_written", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "endpoint"}); err != nil {
		return nil, err
	}
	tokEp, err := r.postCommit("/v1/endpoints/commit", map[string]any{
		"owner": owner, "config_digest": r.ConfigDigest(), "endpoints": st["gateway_endpoints"],
	})
	if err != nil {
		return nil, err
	}
	_ = r.SetMeta("token_endpoint", tokEp)
	_ = r.AppendJournal(JournalRecord{Event: "endpoint_commit", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "endpoint", Token: tokEp})
	if err := r.WriteState(st); err != nil {
		return nil, err
	}
	if failAfter == "endpoint_commit" {
		_ = r.AppendJournal(JournalRecord{Event: "endpoint_commit_lost", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "endpoint", Token: tokEp})
		return nil, errors.New("injected failure after endpoint_commit")
	}
	_ = r.AppendJournal(JournalRecord{Event: "audit_plan_written", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "audit"})
	_ = r.AppendJournal(JournalRecord{Event: "state_moves_committed", Owner: owner, ConfigDigest: r.ConfigDigest(), Stage: "moved"})
	if err := r.WriteState(st); err != nil {
		return nil, err
	}
	sd := digestMap(st)
	if err := r.AppendJournal(JournalRecord{Event: "apply_committed", Owner: owner, ConfigDigest: r.ConfigDigest(), StateDigest: sd, Token: tokEp}); err != nil {
		return nil, err
	}
	return map[string]any{
		"applied": true, "owner": owner, "config_digest": r.ConfigDigest(),
		"controlplane_token_route": tokRoute, "controlplane_token_endpoint": tokEp, "state_digest": sd,
	}, nil
}

func (r *Recovery) ValidateCIDRs(obs *Observed) error {
	_, vpc, err := net.ParseCIDR(str(r.Config["vpc_cidr"]))
	if err != nil {
		return fmt.Errorf("invalid vpc_cidr")
	}
	type nm struct {
		name string
		n    *net.IPNet
	}
	seen := []nm{}
	for _, s := range maps(r.Config["subnets"]) {
		_, n, e := net.ParseCIDR(str(s["cidr"]))
		if e != nil {
			return fmt.Errorf("invalid subnet cidr %s", str(s["name"]))
		}
		if !subnetOf(n, vpc) {
			return fmt.Errorf("subnet %s outside vpc_cidr", str(s["name"]))
		}
		for _, p := range seen {
			if overlaps(n, p.n) {
				return fmt.Errorf("subnet %s overlaps %s", str(s["name"]), p.name)
			}
		}
		seen = append(seen, nm{str(s["name"]), n})
	}
	by := map[string]bool{}
	for _, res := range maps(obs.Imports["resources"]) {
		cidr := str(res["cidr"])
		if cidr != "" {
			if by[cidr] {
				return fmt.Errorf("ambiguous imported cidr %s", cidr)
			}
			by[cidr] = true
		}
	}
	return nil
}

func (r *Recovery) ValidateNATs(obs *Observed) error {
	for _, s := range maps(r.Config["subnets"]) {
		if str(s["tier"]) == "app" {
			az := str(s["az"])
			if r.NATForAZ(obs, az) == "" {
				return fmt.Errorf("missing nat gateway for app az %s", az)
			}
		}
	}
	return nil
}

func (r *Recovery) ValidateEndpoints(obs *Observed) error {
	for _, ep := range maps(r.Config["gateway_endpoints"]) {
		svc := str(ep["service"])
		if svc != "s3" && svc != "dynamodb" {
			return fmt.Errorf("unsupported gateway endpoint service %s", svc)
		}
		obsEP := r.Endpoint(obs, svc)
		if obsEP != nil && !r.EndpointAccountOK(obsEP) {
			return fmt.Errorf("endpoint policy account mismatch for %s", svc)
		}
	}
	return nil
}

func (r *Recovery) ValidateAudit(obs *Observed) error {
	flow := mapMap(obs.Audit, "flow_log")
	arn := str(flow["log_group_arn"])
	if arn == "" {
		arn = str(mapMap(r.Config, "flow_log")["log_group_arn"])
	}
	acct := str(r.Config["account_id"])
	if arn != "" && acct != "" && !strings.Contains(arn, ":"+acct+":") {
		return fmt.Errorf("flow-log destination account mismatch")
	}
	return nil
}

func (r *Recovery) NATForAZ(obs *Observed, az string) string {
	for _, n := range maps(obs.NatHealth["nat_gateways"]) {
		if str(n["az"]) == az && str(n["state"]) == "available" {
			return str(n["id"])
		}
	}
	// Fall back to desired listing only when health marks available via desired id match.
	for _, n := range maps(r.Config["nat_gateways"]) {
		if str(n["az"]) == az {
			for _, h := range maps(obs.NatHealth["nat_gateways"]) {
				if str(h["id"]) == str(n["id"]) && str(h["state"]) == "available" {
					return str(n["id"])
				}
			}
		}
	}
	return ""
}

func (r *Recovery) ObservedRoute(obs *Observed, tier, az string) map[string]any {
	for _, rt := range obs.RouteTables {
		if str(rt["tier"]) == tier && str(rt["az"]) == az {
			return rt
		}
	}
	return nil
}

func (r *Recovery) ImportByCIDR(obs *Observed) map[string]map[string]any {
	out := map[string]map[string]any{}
	for _, res := range maps(obs.Imports["resources"]) {
		cidr := str(res["cidr"])
		if cidr != "" {
			out[cidr] = res
		}
	}
	return out
}

func (r *Recovery) RouteActions(rts []map[string]any) []map[string]any {
	out := []map[string]any{}
	for _, rt := range rts {
		if str(rt["tier"]) == "app" {
			out = append(out, map[string]any{"action": "ensure_default_route", "route_table_id": rt["id"], "target": routeTarget(rt, "0.0.0.0/0")})
		}
		if str(rt["tier"]) == "data" && routeTarget(rt, "0.0.0.0/0") != "" {
			out = append(out, map[string]any{"action": "remove_default_route", "route_table_id": rt["id"]})
		}
	}
	return out
}

func (r *Recovery) RenderEndpoints(obs *Observed, outputs map[string]any) ([]map[string]any, []map[string]any) {
	app := stringAny(outputs["private_app_route_table_ids"])
	eps := []map[string]any{}
	acts := []map[string]any{}
	services := []string{}
	for _, ep := range maps(r.Config["gateway_endpoints"]) {
		services = append(services, str(ep["service"]))
	}
	sort.Strings(services)
	for _, svc := range services {
		obsEP := r.Endpoint(obs, svc)
		eid := id("vpce", str(r.Config["environment"]), svc)
		policy := map[string]any{"Statement": []any{map[string]any{
			"Action": []any{svc + ":*"}, "Resource": []any{"*"},
			"Condition": map[string]any{"StringEquals": map[string]any{"aws:PrincipalAccount": str(r.Config["account_id"])}},
		}}}
		tags := map[string]any{"ManagedBy": "terraform-aws-vpc-module", "Environment": str(r.Config["environment"])}
		meta := map[string]any{}
		if obsEP != nil {
			if str(obsEP["id"]) != "" {
				eid = str(obsEP["id"])
			}
			if obsEP["policy"] != nil {
				policy = obsEP["policy"].(map[string]any)
			}
			if obsEP["tags"] != nil {
				tags = obsEP["tags"].(map[string]any)
			}
			if obsEP["metadata"] != nil {
				meta = obsEP["metadata"].(map[string]any)
			}
		}
		eps = append(eps, map[string]any{"id": eid, "service": svc, "route_table_ids": app, "policy": policy, "tags": tags, "metadata": meta})
		if obsEP != nil && !sameStrings(app, stringAny(obsEP["route_table_ids"])) {
			acts = append(acts, map[string]any{"action": "update_endpoint_association", "endpoint_id": eid, "service": svc, "route_table_ids": app})
		}
	}
	return eps, acts
}

func (r *Recovery) Endpoint(obs *Observed, svc string) map[string]any {
	for _, ep := range obs.Endpoints {
		if str(ep["service"]) == svc {
			return ep
		}
	}
	return nil
}

func (r *Recovery) EndpointAccountOK(ep map[string]any) bool {
	b, _ := json.Marshal(ep["policy"])
	return strings.Contains(string(b), str(r.Config["account_id"]))
}

func (r *Recovery) MovedActions(obs *Observed, subs []map[string]any) []map[string]any {
	appByCIDR := map[string]string{}
	for _, s := range subs {
		if str(s["tier"]) == "app" {
			appByCIDR[str(s["cidr"])] = str(s["address"])
		}
	}
	out := []map[string]any{}
	seen := map[string]bool{}
	for _, res := range maps(obs.Imports["resources"]) {
		to := appByCIDR[str(res["cidr"])]
		from := str(res["address"])
		if to != "" && from != "" && from != to && !seen[from] {
			out = append(out, map[string]any{"action": "moved", "from": from, "to": to, "id": res["id"]})
			seen[from] = true
		}
	}
	sort.Slice(out, func(i, j int) bool { return str(out[i]["from"]) < str(out[j]["from"]) })
	return out
}

func (r *Recovery) RenderAudit(obs *Observed, subs []map[string]any, env string) (any, any, []map[string]any) {
	flowInv := mapMap(obs.Audit, "flow_log")
	flMeta := map[string]any{}
	if flowInv["metadata"] != nil {
		flMeta = flowInv["metadata"].(map[string]any)
	}
	arn := str(mapMap(r.Config, "flow_log")["log_group_arn"])
	if arn == "" {
		arn = str(flowInv["log_group_arn"])
	}
	fl := map[string]any{
		"id": first(str(flowInv["id"]), id("fl", env, "vpc")), "traffic_type": "ALL",
		"destination": first(str(mapMap(r.Config, "flow_log")["destination"]), str(flowInv["destination"])),
		"iam_policy":  map[string]any{"Action": []any{"logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"}, "Resource": arn + ":*"},
		"log_format":  "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${action}",
		"subnet_ids":  allSubnetIDs(subs), "metadata": flMeta,
	}
	cidrs := stringAny(mapMap(r.Config, "resolver")["allowed_cidrs"])
	rules := []map[string]any{}
	for _, p := range []string{"tcp", "udp"} {
		rules = append(rules, map[string]any{"protocol": p, "from_port": 53, "to_port": 53, "cidr_blocks": cidrs, "owner": "terraform-aws-vpc-module"})
	}
	sgInv := mapMap(obs.Audit, "resolver_security_group")
	sgMeta := map[string]any{}
	if sgInv["metadata"] != nil {
		sgMeta = sgInv["metadata"].(map[string]any)
	}
	sg := map[string]any{
		"id": first(str(sgInv["id"]), id("sg", env, "resolver-inbound")), "ingress": rules,
		"egress": []any{map[string]any{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": []any{r.Config["vpc_cidr"]}}}, "metadata": sgMeta,
	}
	drift := []map[string]any{}
	for _, rule := range maps(sgInv["ingress"]) {
		if str(rule["owner"]) == "manual" {
			drift = append(drift, map[string]any{"action": "report_only", "resource": "resolver_security_group", "field": "ingress", "observed": rule, "reason": "manual rule preserved"})
		}
	}
	if str(flowInv["scope"]) != "subnet" {
		drift = append(drift, map[string]any{"action": "update_flow_log", "resource": "flow_log", "from": flowInv["scope"], "to": "subnet"})
	}
	return fl, sg, drift
}

func (r *Recovery) dbPath() string {
	return filepath.Join(r.Root, "var", "reconcile", "state.db")
}

func (r *Recovery) openDB() (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(r.dbPath()), 0755); err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", r.dbPath())
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(`PRAGMA journal_mode=WAL;`); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func (r *Recovery) EnsureDB() error {
	db, err := r.openDB()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`
CREATE TABLE IF NOT EXISTS journal (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  owner TEXT,
  config_digest TEXT,
  stage TEXT,
  state_digest TEXT,
  token TEXT,
  payload_json TEXT NOT NULL,
  row_checksum TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recovered (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  state_json TEXT NOT NULL,
  state_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);`)
	return err
}

func rowChecksum(payload string) string {
	h := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(h[:])
}

func (r *Recovery) AppendJournal(rec JournalRecord) error {
	db, err := r.openDB()
	if err != nil {
		return err
	}
	defer db.Close()
	b, _ := json.Marshal(rec)
	sum := rowChecksum(string(b))
	_, err = db.Exec(`INSERT INTO journal(event, owner, config_digest, stage, state_digest, token, payload_json, row_checksum)
VALUES(?,?,?,?,?,?,?,?)`, rec.Event, rec.Owner, rec.ConfigDigest, rec.Stage, rec.StateDigest, rec.Token, string(b), sum)
	return err
}

func (r *Recovery) ReadJournal() ([]JournalRecord, error) {
	db, err := r.openDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query(`SELECT seq, payload_json, row_checksum FROM journal ORDER BY seq ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	type raw struct {
		seq int
		payload, sum string
	}
	all := []raw{}
	for rows.Next() {
		var item raw
		if err := rows.Scan(&item.seq, &item.payload, &item.sum); err != nil {
			return nil, err
		}
		all = append(all, item)
	}
	recs := []JournalRecord{}
	for i, item := range all {
		if rowChecksum(item.payload) != item.sum || !json.Valid([]byte(item.payload)) {
			if i == len(all)-1 {
				break
			}
			return nil, fmt.Errorf("journal corruption before tail")
		}
		var rec JournalRecord
		if err := json.Unmarshal([]byte(item.payload), &rec); err != nil {
			if i == len(all)-1 {
				break
			}
			return nil, fmt.Errorf("journal corruption before tail")
		}
		recs = append(recs, rec)
	}
	return recs, nil
}

func (r *Recovery) RepairJournal() error {
	db, err := r.openDB()
	if err != nil {
		return err
	}
	defer db.Close()
	rows, err := db.Query(`SELECT seq, payload_json, row_checksum FROM journal ORDER BY seq ASC`)
	if err != nil {
		return err
	}
	defer rows.Close()
	keep := []int{}
	var lastBad *int
	idx := 0
	seqs := []int{}
	payloads := []string{}
	sums := []string{}
	for rows.Next() {
		var seq int
		var payload, sum string
		if err := rows.Scan(&seq, &payload, &sum); err != nil {
			return err
		}
		seqs = append(seqs, seq)
		payloads = append(payloads, payload)
		sums = append(sums, sum)
	}
	for i := range seqs {
		ok := rowChecksum(payloads[i]) == sums[i] && json.Valid([]byte(payloads[i]))
		if !ok {
			if i == len(seqs)-1 {
				lastBad = &seqs[i]
				break
			}
			return fmt.Errorf("journal corruption before tail")
		}
		keep = append(keep, seqs[i])
		idx++
	}
	if lastBad != nil {
		_, err = db.Exec(`DELETE FROM journal WHERE seq = ?`, *lastBad)
		return err
	}
	_ = keep
	return nil
}

func (r *Recovery) CheckOwner(owner string) error {
	recs, err := r.ReadJournal()
	if err != nil {
		return err
	}
	for _, rec := range recs {
		if rec.Owner != "" && rec.Owner != owner {
			return fmt.Errorf("stale owner %s cannot resume owner %s", owner, rec.Owner)
		}
		if rec.ConfigDigest != "" && rec.ConfigDigest != r.ConfigDigest() {
			return fmt.Errorf("config digest changed during recovery")
		}
	}
	return nil
}

func (r *Recovery) AlreadyCommitted(owner string) bool {
	current, _, err := r.LoadState()
	if err != nil || current == nil {
		return false
	}
	if str(current["schema_version"]) != schemaVersion {
		return false
	}
	recs, err := r.ReadJournal()
	if err != nil {
		return false
	}
	for _, rec := range recs {
		if rec.Event == "apply_committed" && rec.Owner == owner && rec.ConfigDigest == r.ConfigDigest() {
			return true
		}
	}
	return false
}

func (r *Recovery) WriteState(st map[string]any) error {
	db, err := r.openDB()
	if err != nil {
		return err
	}
	defer db.Close()
	b, err := json.Marshal(st)
	if err != nil {
		return err
	}
	_, err = db.Exec(`INSERT INTO recovered(id, state_json, state_digest) VALUES(1, ?, ?)
ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json, state_digest=excluded.state_digest`, string(b), digestMap(st))
	return err
}

func (r *Recovery) LoadState() (map[string]any, map[string]string, error) {
	if _, err := os.Stat(r.dbPath()); os.IsNotExist(err) {
		return nil, map[string]string{}, nil
	}
	db, err := r.openDB()
	if err != nil {
		return nil, nil, err
	}
	defer db.Close()
	var raw string
	err = db.QueryRow(`SELECT state_json FROM recovered WHERE id = 1`).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, map[string]string{}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	var st map[string]any
	if err := json.Unmarshal([]byte(raw), &st); err != nil {
		return nil, nil, err
	}
	meta := map[string]string{}
	mrows, err := db.Query(`SELECT key, value FROM meta`)
	if err == nil {
		defer mrows.Close()
		for mrows.Next() {
			var k, v string
			_ = mrows.Scan(&k, &v)
			meta[k] = v
		}
	}
	return st, meta, nil
}

func (r *Recovery) SetMeta(key, value string) error {
	db, err := r.openDB()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value`, key, value)
	return err
}

func (r *Recovery) ConfigDigest() string { return digestMap(r.Config) }

func readMap(path string) (map[string]any, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	return m, nil
}

func printJSON(obj any) { b, _ := json.MarshalIndent(obj, "", "  "); fmt.Println(string(b)) }
func failJSON(j bool, err error) {
	if j {
		printJSON(map[string]any{"valid": false, "error": err.Error()})
	} else {
		fmt.Fprintln(os.Stderr, err)
	}
	os.Exit(2)
}
func die(msg string) { fmt.Fprintln(os.Stderr, msg); os.Exit(1) }
func str(v any) string {
	if v == nil {
		return ""
	}
	return fmt.Sprint(v)
}
func maps(v any) []map[string]any {
	arr, ok := v.([]any)
	if !ok {
		return nil
	}
	out := []map[string]any{}
	for _, x := range arr {
		if m, ok := x.(map[string]any); ok {
			out = append(out, m)
		}
	}
	return out
}
func mapMap(m map[string]any, k string) map[string]any {
	if x, ok := m[k].(map[string]any); ok {
		return x
	}
	return map[string]any{}
}
func stringAny(v any) []string {
	arr, ok := v.([]any)
	if !ok {
		if ss, ok := v.([]string); ok {
			return append([]string{}, ss...)
		}
		return nil
	}
	out := []string{}
	for _, x := range arr {
		out = append(out, str(x))
	}
	sort.Strings(out)
	return out
}
func id(prefix string, parts ...any) string {
	ss := []string{}
	for _, p := range parts {
		s := strings.ReplaceAll(strings.ReplaceAll(str(p), "/", "_"), ".", "_")
		ss = append(ss, s)
	}
	return prefix + "-" + strings.Join(ss, "-")
}
func azSuffix(az string) string {
	if az == "" {
		return "unknown"
	}
	return az[len(az)-1:]
}
func ids(subs []map[string]any, tier string) []string {
	out := []string{}
	for _, s := range subs {
		if str(s["tier"]) == tier {
			out = append(out, str(s["id"]))
		}
	}
	sort.Strings(out)
	return out
}
func rtids(rts []map[string]any, tier string) []string {
	out := []string{}
	for _, r := range rts {
		if str(r["tier"]) == tier {
			out = append(out, str(r["id"]))
		}
	}
	sort.Strings(out)
	return out
}
func allSubnetIDs(subs []map[string]any) []string {
	out := []string{}
	for _, s := range subs {
		out = append(out, str(s["id"]))
	}
	sort.Strings(out)
	return out
}
func routeTarget(rt map[string]any, dest string) string {
	for _, r := range maps(rt["routes"]) {
		if str(r["destination"]) == dest {
			return str(r["target"])
		}
	}
	return ""
}
func first(a, b string) string {
	if a != "" {
		return a
	}
	return b
}
func digestMap(m any) string {
	b, _ := json.Marshal(m)
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
func sameStrings(a, b []string) bool {
	aa := append([]string{}, a...)
	bb := append([]string{}, b...)
	sort.Strings(aa)
	sort.Strings(bb)
	if len(aa) != len(bb) {
		return false
	}
	for i := range aa {
		if aa[i] != bb[i] {
			return false
		}
	}
	return true
}
func subnetOf(child, parent *net.IPNet) bool {
	co, cb := child.Mask.Size()
	po, pb := parent.Mask.Size()
	return cb == pb && co >= po && parent.Contains(child.IP)
}
func overlaps(a, b *net.IPNet) bool { return a.Contains(b.IP) || b.Contains(a.IP) }
