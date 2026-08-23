package model

import "time"

type Desired struct {
	Revision     uint64        `json:"revision"`
	Listeners    []Listener    `json:"listeners"`
	TargetGroups []TargetGroup `json:"target_groups"`
	Rollout      RolloutPolicy `json:"rollout"`
	Limits       Limits        `json:"limits"`
}

type Listener struct {
	Name            string `json:"name"`
	Address         string `json:"address"`
	Port            int    `json:"port"`
	TargetGroup     string `json:"target_group"`
	ProxyProtocolV2 bool   `json:"proxy_protocol_v2"`
	ConnectTimeout  int    `json:"connect_timeout_ms"`
	IdleTimeout     int    `json:"idle_timeout_ms"`
	BufferBytes     int    `json:"buffer_bytes"`
}

type TargetGroup struct {
	Name         string       `json:"name"`
	Policy       string       `json:"policy"`
	ZonePolicy   string       `json:"zone_policy"`
	FailOpen     bool         `json:"fail_open"`
	DrainTimeout int          `json:"drain_timeout_ms"`
	Health       HealthPolicy `json:"health"`
	Targets      []Target     `json:"targets"`
}

type Target struct {
	ID                  string `json:"id"`
	Address             string `json:"address"`
	Port                int    `json:"port"`
	Zone                string `json:"zone"`
	AdministrativeState string `json:"administrative_state"`
	Weight              int    `json:"weight"`
	Incarnation         uint64 `json:"incarnation"`
}

func (t Target) Identity(group string) string {
	return group + "/" + t.ID + "/" + fmtUint(t.Incarnation)
}

func fmtUint(value uint64) string {
	if value == 0 { return "0" }
	var data [20]byte
	position := len(data)
	for value > 0 { position--; data[position] = byte('0' + value%10); value /= 10 }
	return string(data[position:])
}

type HealthPolicy struct {
	Interval           int    `json:"interval_ms"`
	Timeout            int    `json:"timeout_ms"`
	HealthyThreshold   int    `json:"healthy_threshold"`
	UnhealthyThreshold int    `json:"unhealthy_threshold"`
	PassiveFailures    int    `json:"passive_failures"`
	PassiveWindow      int    `json:"passive_window_ms"`
	Ejection           int    `json:"ejection_ms"`
	Send               string `json:"send,omitempty"`
	Expect             string `json:"expect,omitempty"`
}

type RolloutPolicy struct {
	PrepareQuorum           int `json:"prepare_quorum"`
	ActivateQuorum          int `json:"activate_quorum"`
	PrepareTimeout          int `json:"prepare_timeout_ms"`
	ActivateTimeout         int `json:"activate_timeout_ms"`
	AllowedUnavailableZones int `json:"allowed_unavailable_zones"`
}

type Limits struct {
	MaxListeners         int `json:"max_listeners"`
	MaxTargetGroups      int `json:"max_target_groups"`
	MaxTargets           int `json:"max_targets"`
	MaxFrameBytes        int `json:"max_frame_bytes"`
	MaxQueueMessages     int `json:"max_queue_messages"`
	MaxAuditEvents       int `json:"max_audit_events"`
	RetainedGenerations  int `json:"retained_generations"`
	MaxHealthSamples     int `json:"max_health_samples"`
	MaxConnectionRecords int `json:"max_connection_records"`
	MaxBufferBytes       int `json:"max_buffer_bytes"`
}

type Snapshot struct {
	Generation   uint64        `json:"generation"`
	Revision     uint64        `json:"revision"`
	CreatedAt    string        `json:"created_at"`
	Listeners    []Listener    `json:"listeners"`
	TargetGroups []TargetGroup `json:"target_groups"`
	Limits       Limits        `json:"limits"`
}

type Envelope struct {
	Type       string         `json:"type"`
	NodeID     string         `json:"node_id"`
	SessionID  string         `json:"session_id"`
	Sequence   uint64         `json:"sequence"`
	SentAt     string         `json:"sent_at"`
	Generation uint64         `json:"generation,omitempty"`
	Digest     string         `json:"digest,omitempty"`
	Body       map[string]any `json:"body"`
}

type Rollout struct {
	Generation       uint64                  `json:"generation"`
	Digest           string                  `json:"digest"`
	Revision         uint64                  `json:"revision"`
	Phase            string                  `json:"phase"`
	PreviousActive   uint64                  `json:"previous_active"`
	PrepareQuorum    int                     `json:"prepare_quorum"`
	ActivateQuorum   int                     `json:"activate_quorum"`
	Deadline         time.Time               `json:"deadline"`
	NodeResponses    map[string]NodeResponse `json:"node_responses"`
}

type NodeResponse struct {
	SessionID  string `json:"session_id"`
	Sequence   uint64 `json:"sequence"`
	Generation uint64 `json:"generation"`
	Digest     string `json:"digest"`
	State      string `json:"state"`
	Reason     string `json:"reason,omitempty"`
}

type NodeStatus struct {
	NodeID             string    `json:"node_id"`
	SessionID          string    `json:"session_id"`
	Zone               string    `json:"zone"`
	Connected          bool      `json:"connected"`
	LastSequence       uint64    `json:"last_sequence"`
	PreparedGeneration uint64    `json:"prepared_generation"`
	ActiveGeneration   uint64    `json:"active_generation"`
	LastSeen           time.Time `json:"last_seen"`
}