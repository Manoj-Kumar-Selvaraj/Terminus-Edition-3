package api

import (
	"encoding/json"
	"errors"
	"net/http"

	"outbox/internal/claim"
	"outbox/internal/policy"
	"outbox/internal/quota"
	"outbox/internal/store"
	"outbox/internal/validate"
)

type errorBody struct {
	Error string `json:"error"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeJSON(w, http.StatusNotFound, errorBody{Error: "not_found"})
	case errors.Is(err, store.ErrConflict):
		writeJSON(w, http.StatusConflict, errorBody{Error: "conflict"})
	case errors.Is(err, claim.ErrLeaseHeld):
		writeJSON(w, http.StatusConflict, errorBody{Error: "lease_held"})
	case errors.Is(err, claim.ErrLeaseMismatch):
		writeJSON(w, http.StatusConflict, errorBody{Error: "lease_mismatch"})
	case errors.Is(err, claim.ErrUnavailable), errors.Is(err, policy.ErrPaused):
		writeJSON(w, http.StatusConflict, errorBody{Error: "endpoint_unavailable"})
	case errors.Is(err, policy.ErrDisabled):
		writeJSON(w, http.StatusConflict, errorBody{Error: "endpoint_disabled"})
	case errors.Is(err, claim.ErrBadStatus):
		writeJSON(w, http.StatusConflict, errorBody{Error: "invalid_status"})
	case errors.Is(err, quota.ErrExceeded):
		writeJSON(w, http.StatusTooManyRequests, errorBody{Error: "quota_exceeded"})
	case errors.Is(err, policy.ErrUnauthorized):
		writeJSON(w, http.StatusUnauthorized, errorBody{Error: "unauthorized"})
	case errors.Is(err, validate.ErrEmptyName), errors.Is(err, validate.ErrEmptySlug),
		errors.Is(err, validate.ErrBadURL), errors.Is(err, validate.ErrBadSecret),
		errors.Is(err, validate.ErrBadQuota), errors.Is(err, validate.ErrBadAttempts),
		errors.Is(err, validate.ErrBadPayload), errors.Is(err, validate.ErrBadOwner),
		errors.Is(err, validate.ErrBadOutcome):
		writeJSON(w, http.StatusBadRequest, errorBody{Error: err.Error()})
	default:
		msg := err.Error()
		if msg == "invalid_status" {
			writeJSON(w, http.StatusConflict, errorBody{Error: "invalid_status"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, errorBody{Error: "internal"})
	}
}
