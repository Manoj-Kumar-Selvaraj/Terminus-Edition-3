package model

import "time"

type Tenant struct {
	ID                 string    `json:"id"`
	Name               string    `json:"name"`
	Slug               string    `json:"slug"`
	DeliveriesPerHour  int       `json:"deliveries_per_hour"`
	CreatedAt          time.Time `json:"created_at"`
}

type Endpoint struct {
	ID          string    `json:"id"`
	TenantID    string    `json:"tenant_id"`
	Name        string    `json:"name"`
	URL         string    `json:"url"`
	HMACSecret  string    `json:"hmac_secret"`
	Enabled     bool      `json:"enabled"`
	Paused      bool      `json:"paused"`
	MaxAttempts int       `json:"max_attempts"`
	CreatedAt   time.Time `json:"created_at"`
}

type Event struct {
	ID             string     `json:"id"`
	TenantID       string     `json:"tenant_id"`
	EndpointID     string     `json:"endpoint_id"`
	Payload        any        `json:"payload"`
	IdempotencyKey *string    `json:"idempotency_key"`
	Status         string     `json:"status"`
	AttemptCount   int        `json:"attempt_count"`
	LeaseOwner     *string    `json:"lease_owner"`
	LeaseUntil     *time.Time `json:"lease_until"`
	NextAttemptAt  time.Time  `json:"next_attempt_at"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
}

type Attempt struct {
	ID         string    `json:"id"`
	EventID    string    `json:"event_id"`
	AttemptNo  int       `json:"attempt_no"`
	Outcome    string    `json:"outcome"`
	HTTPStatus int       `json:"http_status"`
	Error      string    `json:"error"`
	CreatedAt  time.Time `json:"created_at"`
}

type AuditEvent struct {
	ID         string         `json:"id"`
	Action     string         `json:"action"`
	EntityType string         `json:"entity_type"`
	EntityID   string         `json:"entity_id"`
	Actor      string         `json:"actor"`
	Detail     map[string]any `json:"detail"`
	CreatedAt  time.Time      `json:"created_at"`
}

type Stats struct {
	Tenants   int            `json:"tenants"`
	Endpoints int            `json:"endpoints"`
	ByStatus  map[string]int `json:"by_status"`
}
