package service

import (
	"context"
	"encoding/json"
	"errors"
	"strings"

	"outbox/internal/audit"
	"outbox/internal/backoff"
	"outbox/internal/canonicaljson"
	"outbox/internal/claim"
	"outbox/internal/delivery"
	"outbox/internal/idempotency"
	"outbox/internal/lease"
	"outbox/internal/metrics"
	"outbox/internal/model"
	"outbox/internal/payload"
	"outbox/internal/policy"
	"outbox/internal/quota"
	"outbox/internal/statusmachine"
	"outbox/internal/store"
	"outbox/internal/validate"
)

type Outbox struct {
	Store    *store.Store
	Claimer  *claim.Service
	Quota    *quota.Service
	Audit    *audit.Writer
	Delivery *delivery.Client
	Metrics  *metrics.Snapshot
	Token    string
	Sync     bool
}

func New(st *store.Store, token string, sync bool) *Outbox {
	return &Outbox{
		Store:    st,
		Claimer:  &claim.Service{Store: st},
		Quota:    &quota.Service{Store: st},
		Audit:    &audit.Writer{Store: st},
		Delivery: delivery.NewClient(),
		Metrics:  metrics.New(),
		Token:    token,
		Sync:     sync,
	}
}

func (o *Outbox) CreateTenant(name, slug string, q int) (model.Tenant, error) {
	if err := validate.TenantName(name); err != nil {
		return model.Tenant{}, err
	}
	if err := validate.TenantSlug(slug); err != nil {
		return model.Tenant{}, err
	}
	if err := validate.Quota(q); err != nil {
		return model.Tenant{}, err
	}
	return o.Store.CreateTenant(name, slug, q)
}

func (o *Outbox) CreateEndpoint(tenantID, name, url, secret string, enabled bool, maxAttempts int) (model.Endpoint, error) {
	if _, err := o.Store.GetTenant(tenantID); err != nil {
		return model.Endpoint{}, err
	}
	if err := validate.TenantName(name); err != nil {
		return model.Endpoint{}, err
	}
	if err := validate.EndpointURL(url); err != nil {
		return model.Endpoint{}, err
	}
	if err := validate.HMACSecret(secret); err != nil {
		return model.Endpoint{}, err
	}
	if err := validate.MaxAttempts(maxAttempts); err != nil {
		return model.Endpoint{}, err
	}
	return o.Store.CreateEndpoint(tenantID, name, url, secret, enabled, maxAttempts)
}

func (o *Outbox) Enqueue(endpointID string, body any, idem *string) (model.Event, bool, error) {
	ep, err := o.Store.GetEndpoint(endpointID)
	if err != nil {
		return model.Event{}, false, err
	}
	if err := policy.CanEnqueue(ep); err != nil {
		return model.Event{}, false, err
	}
	tenant, err := o.Store.GetTenant(ep.TenantID)
	if err != nil {
		return model.Event{}, false, err
	}
	now := o.Store.Now()
	if err := o.Quota.Check(tenant, now); err != nil {
		o.Metrics.Inc(&o.Metrics.QuotaHits)
		return model.Event{}, false, err
	}
	raw, err := encodeEnqueuePayload(body)
	if err != nil {
		return model.Event{}, false, err
	}
	if !payload.IsObject(raw) {
		return model.Event{}, false, validate.ErrBadPayload
	}
	raw = payload.MustCompact(raw)
	if err := validate.PayloadByteBudget(raw, 1<<20); err != nil {
		return model.Event{}, false, err
	}

	var idemKey *string
	if idem != nil {
		if n, ok := idempotency.Prepare(*idem); ok {
			idemKey = &n
		} else if strings.TrimSpace(*idem) != "" {
			return model.Event{}, false, validate.ErrBadPayload
		}
	}

	ev, err := o.Store.InsertEvent(ep.TenantID, ep.ID, raw, idemKey, model.StatusPending)
	if errors.Is(err, store.ErrConflict) && idemKey != nil {
		existing, gerr := o.Store.GetEventByIdempotency(ep.ID, *idemKey)
		if gerr != nil {
			return model.Event{}, false, gerr
		}
		return existing, false, nil
	}
	if err != nil {
		return model.Event{}, false, err
	}
	detail := map[string]any{"endpoint_id": ep.ID}
	if idemKey != nil {
		detail["idem_fp"] = idempotency.Fingerprint(ep.ID, *idemKey)
		detail["idem_scope"] = idempotency.ScopeKey(ep.ID, *idemKey)
	}
	_ = o.Audit.Write(model.ActionEnqueue, "event", ev.ID, "", detail)
	o.Metrics.Inc(&o.Metrics.Enqueued)
	return ev, true, nil
}

func encodeEnqueuePayload(body any) ([]byte, error) {
	switch t := body.(type) {
	case map[string]any:
		b, err := canonicaljson.MarshalObject(t)
		if err != nil {
			return nil, validate.ErrBadPayload
		}
		return b, nil
	default:
		return validate.PayloadObject(body)
	}
}

func (o *Outbox) Claim(eventID, owner string, leaseSeconds int) (model.Event, error) {
	if err := validate.LeaseOwner(owner); err != nil {
		return model.Event{}, err
	}
	ev, err := o.Store.GetEvent(eventID)
	if err != nil {
		return model.Event{}, err
	}
	ep, err := o.Store.GetEndpoint(ev.EndpointID)
	if err != nil {
		return model.Event{}, err
	}
	if err := statusmachine.MustAllow(ev.Status, statusmachine.ClaimTarget()); err != nil {
		return model.Event{}, claim.ErrBadStatus
	}
	leaseSeconds = lease.DefaultSeconds(leaseSeconds)
	now := o.Store.Now()
	out, err := o.Claimer.Acquire(ev, ep, owner, leaseSeconds, now)
	if err != nil {
		if errors.Is(err, claim.ErrLeaseHeld) {
			o.Metrics.Inc(&o.Metrics.Lease409)
		}
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionClaim, "event", out.ID, owner, map[string]any{
		"lease_seconds": leaseSeconds,
		"lease_remaining_ms": lease.Remaining(out.LeaseUntil, now).Milliseconds(),
	})
	o.Metrics.Inc(&o.Metrics.Claimed)
	return out, nil
}

func (o *Outbox) Complete(eventID, owner, outcome string, httpStatus int, errMsg string) (model.Event, error) {
	if err := validate.LeaseOwner(owner); err != nil {
		return model.Event{}, err
	}
	if err := validate.Outcome(outcome); err != nil {
		return model.Event{}, err
	}
	ev, err := o.Store.GetEvent(eventID)
	if err != nil {
		return model.Event{}, err
	}
	ep, err := o.Store.GetEndpoint(ev.EndpointID)
	if err != nil {
		return model.Event{}, err
	}
	tenant, err := o.Store.GetTenant(ev.TenantID)
	if err != nil {
		return model.Event{}, err
	}
	now := o.Store.Now()
	if err := o.Claimer.AssertHolder(ev, owner, now); err != nil {
		return model.Event{}, err
	}
	attemptNo := ev.AttemptCount + 1
	if outcome == model.OutcomeDelivered {
		if _, ok := statusmachine.AfterSuccess(ev.Status); !ok {
			return model.Event{}, claim.ErrBadStatus
		}
		if err := statusmachine.MustAllow(ev.Status, model.StatusDelivered); err != nil {
			return model.Event{}, claim.ErrBadStatus
		}
		if err := o.Quota.Check(tenant, now); err != nil {
			o.Metrics.Inc(&o.Metrics.QuotaHits)
			return model.Event{}, err
		}
		if _, err := o.Store.InsertAttempt(ev.ID, ev.TenantID, attemptNo, model.OutcomeDelivered, httpStatus, ""); err != nil {
			return model.Event{}, err
		}
		if err := o.Store.MarkDelivered(ev.ID); err != nil {
			return model.Event{}, err
		}
		_ = o.Audit.Write(model.ActionDeliverOK, "event", ev.ID, owner, map[string]any{"http_status": httpStatus})
		o.Metrics.Inc(&o.Metrics.Delivered)
		return o.Store.GetEvent(ev.ID)
	}

	if _, err := o.Store.InsertAttempt(ev.ID, ev.TenantID, attemptNo, model.OutcomeFailed, httpStatus, errMsg); err != nil {
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionDeliverFail, "event", ev.ID, owner, map[string]any{"http_status": httpStatus, "error": errMsg})
	o.Metrics.Inc(&o.Metrics.Failed)

	nextStatus := statusmachine.AfterFailure(attemptNo, ep.MaxAttempts)
	if err := statusmachine.MustAllow(ev.Status, nextStatus); err != nil {
		return model.Event{}, claim.ErrBadStatus
	}
	nextAt := backoff.NextAttemptAt(now, attemptNo)
	if err := o.Store.ClearEventLease(ev.ID, nextStatus, nextAt, attemptNo); err != nil {
		return model.Event{}, err
	}
	if nextStatus == model.StatusDLQ {
		_ = o.Audit.Write(model.ActionDLQ, "event", ev.ID, owner, map[string]any{"attempt_count": attemptNo})
		o.Metrics.Inc(&o.Metrics.DLQ)
	}
	return o.Store.GetEvent(ev.ID)
}

func (o *Outbox) Deliver(ctx context.Context, eventID, owner string) (model.Event, error) {
	ev, err := o.Store.GetEvent(eventID)
	if err != nil {
		return model.Event{}, err
	}
	ep, err := o.Store.GetEndpoint(ev.EndpointID)
	if err != nil {
		return model.Event{}, err
	}
	now := o.Store.Now()
	if err := o.Claimer.AssertHolder(ev, owner, now); err != nil {
		return model.Event{}, err
	}
	body, err := deliveryBody(ev.Payload)
	if err != nil {
		return model.Event{}, err
	}
	ts := now.Unix()
	res := o.Delivery.Post(ctx, ep.URL, ep.HMACSecret, ev.ID, ts, body)
	if res.OK {
		return o.Complete(eventID, owner, model.OutcomeDelivered, res.HTTPStatus, "")
	}
	return o.Complete(eventID, owner, model.OutcomeFailed, res.HTTPStatus, res.Error)
}

func deliveryBody(v any) ([]byte, error) {
	switch t := v.(type) {
	case map[string]any:
		b, err := canonicaljson.MarshalObject(t)
		if err != nil {
			return nil, err
		}
		return payload.MustCompact(b), nil
	default:
		b, err := json.Marshal(v)
		if err != nil {
			return nil, err
		}
		return payload.MustCompact(b), nil
	}
}

func (o *Outbox) Replay(eventID, bearer string) (model.Event, error) {
	if err := policy.AuthorizeReplay(o.Token, bearer); err != nil {
		return model.Event{}, err
	}
	ev, err := o.Store.GetEvent(eventID)
	if err != nil {
		return model.Event{}, err
	}
	target := statusmachine.ReplayTarget()
	if err := statusmachine.MustAllow(ev.Status, target); err != nil {
		return model.Event{}, errors.New("invalid_status")
	}
	now := o.Store.Now()
	if err := o.Store.ClearEventLease(ev.ID, target, now, ev.AttemptCount); err != nil {
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionReplay, "event", ev.ID, "operator", map[string]any{})
	o.Metrics.Inc(&o.Metrics.Replayed)
	return o.Store.GetEvent(ev.ID)
}

func (o *Outbox) Pause(endpointID string) (model.Endpoint, error) {
	ep, err := o.Store.SetEndpointPaused(endpointID, true)
	if err != nil {
		return model.Endpoint{}, err
	}
	_ = o.Audit.Write(model.ActionPause, "endpoint", ep.ID, "operator", map[string]any{})
	return ep, nil
}

func (o *Outbox) Resume(endpointID string) (model.Endpoint, error) {
	ep, err := o.Store.SetEndpointPaused(endpointID, false)
	if err != nil {
		return model.Endpoint{}, err
	}
	_ = o.Audit.Write(model.ActionResume, "endpoint", ep.ID, "operator", map[string]any{})
	return ep, nil
}

func (o *Outbox) Stats() (model.Stats, error) {
	by, err := o.Store.CountEventsByStatus()
	if err != nil {
		return model.Stats{}, err
	}
	tc, err := o.Store.CountTenants()
	if err != nil {
		return model.Stats{}, err
	}
	ec, err := o.Store.CountEndpoints()
	if err != nil {
		return model.Stats{}, err
	}
	return model.Stats{Tenants: tc, Endpoints: ec, ByStatus: by}, nil
}

func (o *Outbox) RuntimeMetrics() map[string]any {
	return o.Metrics.View()
}
