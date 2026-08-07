package api

import (
	"net/http"
	"strings"
)

// methodNotAllowed wraps a handler so that only the declared method is accepted.
// Go's pattern mux already routes by method; this helper exists for handlers
// mounted without a method verb in tests or alternate muxes.
func methodNotAllowed(allowed string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !strings.EqualFold(r.Method, allowed) {
			w.Header().Set("Allow", allowed)
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		next(w, r)
	}
}
