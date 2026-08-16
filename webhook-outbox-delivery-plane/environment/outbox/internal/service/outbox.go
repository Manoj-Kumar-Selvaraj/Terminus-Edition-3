package service

import (
	"context"
	"encoding/json"
	"errors"

	"outbox/internal/audit"
	"outbox/internal/backoff"
	"outbox/internal/claim"
	"outbox/internal/delivery"
	"outbox/internal/model"
	"outbox/internal/policy"
	"outbox/internal/quota"
	"outbox/internal/store"
	"outbox/internal/validate"
)

type Outbox struct {
	Store    *store.Store
	Claimer *claim.Service
	Quota    *quota.Service
	Audit    *audit.Writer
	Delivery *delivery.Client
	Token    string
	Sync     bool
}

func New(st *store.Store, token string, sync bool) *Outbox {
	return &Outbox{
		Store:    st,
		Claimer: &claim.Service{Store: st},
		Quota:    &quota.Service{Store: st},
		Audit:    &audit.Writer{Store: st},
		Delivery: delivery.NewClient(),
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

func (o *Outbox) Enqueue(endpointID string, payload any, idem *string) (model.Event, bool, error) {
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
		return model.Event{}, false, err
	}
	raw, err := validate.PayloadObject(payload)
	if err != nil {
		return model.Event{}, false, err
	}
	if idem != nil {
		key := *idem
		if key == "" {
			idem = nil
		}
	}
	ev, err := o.Store.InsertEvent(ep.TenantID, ep.ID, raw, idem, model.StatusPending)
	if errors.Is(err, store.ErrConflict) && idem != nil {
		existing, gerr := o.Store.GetEventByIdempotency(ep.ID, *idem)
		if gerr != nil {
			return model.Event{}, false, gerr
		}
		return existing, false, nil
	}
	if err != nil {
		return model.Event{}, false, err
	}
	_ = o.Audit.Write(model.ActionEnqueue, "event", ev.ID, "", map[string]any{"endpoint_id": ep.ID})
	return ev, true, nil
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
	now := o.Store.Now()
	out, err := o.Claimer.Acquire(ev, ep, owner, leaseSeconds, now)
	if err != nil {
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionClaim, "event", out.ID, owner, map[string]any{"lease_seconds": leaseSeconds})
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
		if err := o.Quota.Check(tenant, now); err != nil {
			return model.Event{}, err
		}
		if _, err := o.Store.InsertAttempt(ev.ID, ev.TenantID, attemptNo, model.OutcomeDelivered, httpStatus, ""); err != nil {
			return model.Event{}, err
		}
		if err := o.Store.MarkDelivered(ev.ID); err != nil {
			return model.Event{}, err
		}
		_ = o.Audit.Write(model.ActionDeliverOK, "event", ev.ID, owner, map[string]any{"http_status": httpStatus})
		return o.Store.GetEvent(ev.ID)
	}

	if _, err := o.Store.InsertAttempt(ev.ID, ev.TenantID, attemptNo, model.OutcomeFailed, httpStatus, errMsg); err != nil {
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionDeliverFail, "event", ev.ID, owner, map[string]any{"http_status": httpStatus, "error": errMsg})

	nextStatus := model.StatusPending
	if attemptNo >= ep.MaxAttempts {
		nextStatus = model.StatusDLQ
	}
	nextAt := backoff.NextAttemptAt(now, attemptNo)
	if err := o.Store.ClearEventLease(ev.ID, nextStatus, nextAt, attemptNo); err != nil {
		return model.Event{}, err
	}
	if nextStatus == model.StatusDLQ {
		_ = o.Audit.Write(model.ActionDLQ, "event", ev.ID, owner, map[string]any{"attempt_count": attemptNo})
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
	body, err := json.Marshal(ev.Payload)
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

func (o *Outbox) Replay(eventID, bearer string) (model.Event, error) {
	if err := policy.AuthorizeReplay(o.Token, bearer); err != nil {
		return model.Event{}, err
	}
	ev, err := o.Store.GetEvent(eventID)
	if err != nil {
		return model.Event{}, err
	}
	if ev.Status != model.StatusDLQ {
		return model.Event{}, errors.New("invalid_status")
	}
	now := o.Store.Now()
	if err := o.Store.ClearEventLease(ev.ID, model.StatusPending, now, ev.AttemptCount); err != nil {
		return model.Event{}, err
	}
	_ = o.Audit.Write(model.ActionReplay, "event", ev.ID, "operator", map[string]any{})
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
