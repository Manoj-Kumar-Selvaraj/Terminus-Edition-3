package main

import (
	"bytes"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

func main() {
	endpoint := flag.String("endpoint", "http://127.0.0.1:16080", "management endpoint")
	key := flag.String("idempotency-key", "", "apply idempotency key")
	flag.Parse()
	if flag.NArg() < 1 { fatal("usage: lbctl [flags] apply FILE | status | nodes | audit | ready") }
	command := flag.Arg(0); method, path := "GET", "/v1/"+command; var body io.Reader
	if command == "apply" { if flag.NArg() != 2 || *key == "" { fatal("apply requires FILE and --idempotency-key") }; data, err := os.ReadFile(flag.Arg(1)); if err != nil { fatal(err.Error()) }; body = bytes.NewReader(data); method = "POST"; path = "/v1/apply" }
	if command == "ready" { path = "/ready" }
	if command != "apply" && command != "status" && command != "nodes" && command != "audit" && command != "ready" { fatal("unknown command") }
	request, err := http.NewRequest(method, strings.TrimRight(*endpoint, "/")+path, body); if err != nil { fatal(err.Error()) }
	if *key != "" { request.Header.Set("Idempotency-Key", *key) }; request.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout:30*time.Second}; response, err := client.Do(request); if err != nil { fatal(err.Error()) }; defer response.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(response.Body, 16<<20)); fmt.Println(string(data)); if response.StatusCode >= 300 { os.Exit(1) }
}

func fatal(message string) { fmt.Fprintln(os.Stderr, message); os.Exit(2) }