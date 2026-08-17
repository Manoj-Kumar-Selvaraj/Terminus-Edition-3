package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"

	"fleetrollout/controller"
	"fleetrollout/internal/controlplane"
	"fleetrollout/internal/journal"
	"fleetrollout/internal/stateio"
	"fleetrollout/internal/types"
)

func load(path string) (types.Value, error) {
	result := types.Value{}
	if err := stateio.ReadJSON(path, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func writeError(outPath string, err error) {
	result := types.Value{"valid": false, "error": err.Error()}
	if outPath != "" {
		_ = stateio.AtomicWrite(outPath, result)
	} else {
		data, _ := json.MarshalIndent(result, "", "  ")
		fmt.Fprintln(os.Stderr, string(data))
	}
	os.Exit(2)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: fleetctl <plan|apply|validate> [flags]")
		os.Exit(2)
	}
	command := os.Args[1]
	if command != "plan" && command != "apply" && command != "validate" {
		fmt.Fprintln(os.Stderr, "unknown command")
		os.Exit(2)
	}
	flags := flag.NewFlagSet(command, flag.ContinueOnError)
	flags.SetOutput(os.Stderr)
	configPath := flags.String("config", "/app/data/fleet_config.json", "configuration file")
	priorPath := flags.String("prior-state", "", "prior state")
	outPath := flags.String("out", "", "output path")
	statePath := flags.String("state", "/app/var/fleet/ec2_state.json", "local state path")
	journalPath := flags.String("journal", "", "journal path")
	controlPlane := flags.String("control-plane", os.Getenv("FLEET_CONTROL_PLANE"), "control plane base URL")
	if err := flags.Parse(os.Args[2:]); err != nil {
		os.Exit(2)
	}
	if *journalPath == "" {
		*journalPath = *statePath + ".journal.jsonl"
	}
	if *controlPlane == "" {
		*controlPlane = "http://127.0.0.1:18080"
	}
	config, err := load(*configPath)
	if err != nil {
		writeError(*outPath, err)
	}
	prior := types.Value{}
	if *priorPath != "" {
		prior, err = load(*priorPath)
		if err != nil {
			writeError(*outPath, err)
		}
	} else if command == "apply" {
		if _, statErr := os.Stat(*statePath); statErr == nil {
			prior, err = load(*statePath)
			if err != nil {
				writeError(*outPath, err)
			}
		}
	}
	_, repair, err := journal.Repair(*journalPath)
	if err != nil {
		writeError(*outPath, err)
	}
	var result types.Value
	if command == "validate" {
		if err := controller.ValidateConfig(config); err != nil {
			writeError(*outPath, err)
		}
		result = types.Value{"valid": true, "schema_version": config["schema_version"], "environment": config["environment"], "journal_repair": repair}
	} else {
		result, err = controller.Render(config, prior)
		if err != nil {
			writeError(*outPath, err)
		}
		result["journal_repair"] = repair
		if command == "apply" {
			owner := ""
			if rollout := types.Object(config["rollout"]); rollout != nil {
				owner, _ = rollout["owner_token"].(string)
			}
			lost, _ := result["control_plane_response_lost"].(bool)
			client := controlplane.New(*controlPlane)
			status, commitErr := client.Commit(owner, result, lost)
			if commitErr != nil {
				writeError(*outPath, commitErr)
			}
			if status != http.StatusOK && status != http.StatusServiceUnavailable {
				writeError(*outPath, fmt.Errorf("control plane commit failed with status %d", status))
			}
			if err := stateio.AtomicWrite(*statePath, result); err != nil {
				writeError(*outPath, err)
			}
			outputs := types.Object(result["outputs"])
			release := types.Object(result["release_identity"])
			refresh := types.Object(types.Object(result["autoscaling_group"])["instance_refresh"])
			if err := journal.Append(*journalPath, types.Value{
				"operation_id":            outputs["rollout_operation_id"],
				"release_manifest_sha256": release["manifest_sha256"],
				"refresh_status":          refresh["status"],
				"state_digest":            result["state_digest"],
			}); err != nil {
				writeError(*outPath, err)
			}
			if lost || status == http.StatusServiceUnavailable {
				if *outPath != "" {
					_ = stateio.AtomicWrite(*outPath, result)
				}
				os.Exit(3)
			}
		}
	}
	if *outPath != "" {
		if err := stateio.AtomicWrite(*outPath, result); err != nil {
			writeError(*outPath, err)
		}
	} else {
		data, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(data))
	}
}
