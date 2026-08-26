package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"sovereign-lb/internal/catalog"
	"sovereign-lb/internal/fleet"
)

func main() {
	endpoint := flag.String("endpoint", "http://127.0.0.1:16080", "management endpoint")
	key := flag.String("idempotency-key", "", "apply idempotency key")
	root := flag.String("root", os.Getenv("SOVEREIGN_LB_HOME"), "sovereign-lb root for local fleet/scenario commands")
	flag.Parse()
	if flag.NArg() < 1 {
		fatal("usage: lbctl [flags] apply FILE | status | nodes | audit | ready | fleet | scenarios | health | retention | recovery | validate-fleet | list-scenarios")
	}
	command := flag.Arg(0)
	switch command {
	case "validate-fleet":
		validateFleet(*root)
		return
	case "list-scenarios":
		listScenarios(*root)
		return
	}
	method, path := "GET", "/v1/"+command
	var body io.Reader
	if command == "apply" {
		if flag.NArg() != 2 || *key == "" {
			fatal("apply requires FILE and --idempotency-key")
		}
		data, err := os.ReadFile(flag.Arg(1))
		if err != nil {
			fatal(err.Error())
		}
		body = bytes.NewReader(data)
		method = "POST"
		path = "/v1/apply"
	}
	if command == "ready" {
		path = "/ready"
	}
	allowed := map[string]bool{
		"apply": true, "status": true, "nodes": true, "audit": true, "ready": true,
		"fleet": true, "scenarios": true, "health": true, "retention": true, "recovery": true,
	}
	if !allowed[command] {
		fatal("unknown command")
	}
	request, err := http.NewRequest(method, strings.TrimRight(*endpoint, "/")+path, body)
	if err != nil {
		fatal(err.Error())
	}
	if *key != "" {
		request.Header.Set("Idempotency-Key", *key)
	}
	request.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 30 * time.Second}
	response, err := client.Do(request)
	if err != nil {
		fatal(err.Error())
	}
	defer response.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(response.Body, 16<<20))
	fmt.Println(string(data))
	if response.StatusCode >= 300 {
		os.Exit(1)
	}
}

func validateFleet(root string) {
	if root == "" {
		root = "/app/sovereign-lb"
	}
	inventory, err := fleet.LoadInventory(filepath.Join(root, "config", "fleet.json"))
	if err != nil {
		fatal(err.Error())
	}
	profiles, err := fleet.LoadAllProfiles(root, inventory)
	if err != nil {
		fatal(err.Error())
	}
	for _, profile := range profiles {
		if err := fleet.EnsureNodeStateRoot(profile); err != nil {
			fatal(err.Error())
		}
	}
	payload, _ := json.MarshalIndent(map[string]any{
		"nodes":  len(inventory.Nodes),
		"zones":  inventory.Zones(),
		"ok":     true,
		"profile_count": len(profiles),
	}, "", "  ")
	fmt.Println(string(payload))
}

func listScenarios(root string) {
	if root == "" {
		root = "/app/sovereign-lb"
	}
	scenarios, err := catalog.LoadDirectory(filepath.Join(root, "config", "scenarios"))
	if err != nil {
		fatal(err.Error())
	}
	payload, _ := json.MarshalIndent(catalog.Summaries(scenarios), "", "  ")
	fmt.Println(string(payload))
}

func fatal(message string) {
	fmt.Fprintln(os.Stderr, message)
	os.Exit(2)
}
