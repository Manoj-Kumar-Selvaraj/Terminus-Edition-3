package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"outbox/internal/httpx"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	addr := getenv("OUTBOX_ADDR", "127.0.0.1:8080")
	base := "http://" + addr
	token := os.Getenv("OUTBOX_TOKEN")
	cmd := os.Args[1]
	args := os.Args[2:]
	switch cmd {
	case "health":
		if flag(args, "--wait") {
			timeout := parseTimeout(args, 15*time.Second)
			if err := httpx.WaitHTTP(base+"/api/v1/health", timeout); err != nil {
				fatal(err)
			}
		}
		get(base + "/api/v1/health")
	case "wait":
		timeout := parseTimeout(args, 30*time.Second)
		if err := httpx.WaitHTTP(base+"/api/v1/health", timeout); err != nil {
			fatal(err)
		}
		fmt.Println(`{"ready":true}`)
	case "tenants":
		if flag(args, "list") || len(args) == 0 || args[0] == "list" {
			get(base + "/api/v1/tenants")
		} else {
			usage()
			os.Exit(2)
		}
	case "enqueue":
		ep := mustFlag(args, "--endpoint")
		payload := mustFlag(args, "--payload")
		idem := optionalFlag(args, "--idempotency-key")
		body := map[string]any{}
		if err := json.Unmarshal([]byte(payload), &body); err != nil {
			fatal(err)
		}
		req := map[string]any{"payload": body}
		if idem != "" {
			req["idempotency_key"] = idem
		}
		postJSON(base+"/api/v1/endpoints/"+ep+"/events", req, "")
	case "claim":
		ev := mustFlag(args, "--event")
		owner := mustFlag(args, "--owner")
		secs := optionalFlag(args, "--seconds")
		req := map[string]any{"lease_owner": owner}
		if secs != "" {
			var n int
			fmt.Sscanf(secs, "%d", &n)
			req["lease_seconds"] = n
		}
		postJSON(base+"/api/v1/events/"+ev+"/claim", req, "")
	case "deliver":
		ev := mustFlag(args, "--event")
		owner := mustFlag(args, "--owner")
		postJSON(base+"/api/v1/events/"+ev+"/deliver", map[string]any{"lease_owner": owner}, "")
	case "replay":
		ev := mustFlag(args, "--event")
		postJSON(base+"/api/v1/events/"+ev+"/replay", map[string]any{}, token)
	case "pause":
		ep := mustFlag(args, "--endpoint")
		postJSON(base+"/api/v1/endpoints/"+ep+"/pause", map[string]any{}, "")
	case "resume":
		ep := mustFlag(args, "--endpoint")
		postJSON(base+"/api/v1/endpoints/"+ep+"/resume", map[string]any{}, "")
	case "audit":
		limit := optionalFlag(args, "--limit")
		url := base + "/api/v1/audit"
		if limit != "" {
			url += "?limit=" + limit
		}
		get(url)
	default:
		usage()
		os.Exit(2)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "outboxctl health[--wait]|wait|tenants list|enqueue|claim|deliver|replay|pause|resume|audit")
}

func parseTimeout(args []string, def time.Duration) time.Duration {
	raw := optionalFlag(args, "--timeout")
	if raw == "" {
		return def
	}
	if secs, err := strconv.Atoi(raw); err == nil && secs > 0 {
		return time.Duration(secs) * time.Second
	}
	if d, err := time.ParseDuration(raw); err == nil {
		return d
	}
	return def
}

func getenv(k, d string) string {
	v := os.Getenv(k)
	if v == "" {
		return d
	}
	return v
}

func flag(args []string, name string) bool {
	for _, a := range args {
		if a == name {
			return true
		}
	}
	return false
}

func mustFlag(args []string, name string) string {
	v := optionalFlag(args, name)
	if v == "" {
		fatal(fmt.Errorf("missing %s", name))
	}
	return v
}

func optionalFlag(args []string, name string) string {
	for i := 0; i < len(args); i++ {
		if args[i] == name && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(args[i], name+"=") {
			return strings.TrimPrefix(args[i], name+"=")
		}
	}
	return ""
}

func get(url string) {
	resp, err := http.Get(url)
	if err != nil {
		fatal(err)
	}
	defer resp.Body.Close()
	io.Copy(os.Stdout, resp.Body)
	fmt.Println()
}

func postJSON(url string, body any, token string) {
	b, _ := json.Marshal(body)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(b))
	if err != nil {
		fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fatal(err)
	}
	defer resp.Body.Close()
	io.Copy(os.Stdout, resp.Body)
	fmt.Println()
	if resp.StatusCode >= 400 {
		os.Exit(1)
	}
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
