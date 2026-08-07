package store

// Network is a fabric segment that pools attach to.
type Network struct {
	ID     string `json:"id"`
	CIDR   string `json:"cidr"`
	Region string `json:"region"`
	Status string `json:"status"` // must be "ready" before dependents attach
}

// Origin is one backend endpoint inside a pool.
type Origin struct {
	ID      string `json:"id"`
	Host    string `json:"host"`
	Port    int    `json:"port"`
	Healthy bool   `json:"healthy"`
}

// Pool is a color-coded origin set attached to a network.
type Pool struct {
	ID         string   `json:"id"`
	NetworkID  string   `json:"network_id"`
	Color      string   `json:"color"` // "blue" | "green"
	MinHealthy int      `json:"min_healthy"`
	Origins    []Origin `json:"origins"`
}

// Canary splits traffic between a blue and green pool.
type Canary struct {
	ID          string `json:"id"`
	BluePool    string `json:"blue_pool"`
	GreenPool   string `json:"green_pool"`
	WeightGreen int    `json:"weight_green"` // 0–100
}

// WAFRule is one match/action pair inside a WAF policy.
type WAFRule struct {
	ID     string `json:"id"`
	Action string `json:"action"` // "block" | "allow"
	Match  string `json:"match"`
}

// WAF is an edge web-application firewall policy.
type WAF struct {
	ID    string    `json:"id"`
	Mode  string    `json:"mode"` // "enforce" | "detect"
	Rules []WAFRule `json:"rules"`
}

// TLSCert binds a hostname to a certificate fingerprint.
type TLSCert struct {
	ID          string `json:"id"`
	Hostname    string `json:"hostname"`
	Fingerprint string `json:"fingerprint"`
}

// DNSRecord is a zone/name cutover pointing at an origin pool.
type DNSRecord struct {
	Zone                string `json:"zone"`
	Name                string `json:"name"`
	TargetPool          string `json:"target_pool"`
	RequireCanaryWeight int    `json:"require_canary_weight"`
	RequireWAFEnforce   bool   `json:"require_waf_enforce"`
}

// Metrics is the live traffic counter surface.
type Metrics struct {
	Requests          int64   `json:"requests"`
	Errors            int64   `json:"errors"`
	ErrorRatePct      float64 `json:"error_rate_pct"`
	CanaryWeightGreen int     `json:"canary_weight_green"`
	DNSTargetPool     string  `json:"dns_target_pool"`
}

// Snapshot is the full control-plane state returned by GET /v1/snapshot.
type Snapshot struct {
	Networks map[string]Network   `json:"networks"`
	Pools    map[string]Pool      `json:"pools"`
	Canaries map[string]Canary    `json:"canaries"`
	WAFs     map[string]WAF       `json:"wafs"`
	TLS      map[string]TLSCert   `json:"tls"`
	DNS      map[string]DNSRecord `json:"dns"`
	Metrics  Metrics              `json:"metrics"`
}

// ConflictError is returned when an invariant fails (HTTP 409).
type ConflictError struct {
	Msg string
}

func (e *ConflictError) Error() string { return e.Msg }

// ValidationError is returned for malformed input (HTTP 400).
type ValidationError struct {
	Msg string
}

func (e *ValidationError) Error() string { return e.Msg }

// NotFoundError is returned when a referenced object is missing (HTTP 404).
type NotFoundError struct {
	Msg string
}

func (e *NotFoundError) Error() string { return e.Msg }
