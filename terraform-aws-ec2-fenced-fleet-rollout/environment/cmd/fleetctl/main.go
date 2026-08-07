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

	"fleetrollout/controller"
)

func load(path string) (controller.Value, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	result := controller.Value{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func atomicWrite(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	tmp, err := os.CreateTemp(filepath.Dir(path), filepath.Base(path)+".")
	if err != nil {
		return err
	}
	name := tmp.Name()
	defer os.Remove(name)
	if _, err := tmp.Write(data); err == nil {
		err = tmp.Sync()
	}
	if closeErr := tmp.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return err
	}
	return os.Rename(name, path)
}

func repairJournal(path string) ([]controller.Value, controller.Value, error) {
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []controller.Value{}, controller.Value{"truncated_tail": false, "preserved_records": 0}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	lines := strings.Split(strings.TrimSuffix(string(data), "\n"), "\n")
	records := []controller.Value{}
	truncated := false
	for index, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		value := controller.Value{}
		if err := json.Unmarshal([]byte(line), &value); err != nil {
			if index != len(lines)-1 {
				return nil, nil, fmt.Errorf("invalid interior journal record at line %d", index+1)
			}
			truncated = true
			continue
		}
		records = append(records, value)
	}
	if truncated {
		contents := []byte{}
		for _, record := range records {
			line, _ := json.Marshal(record)
			contents = append(contents, line...)
			contents = append(contents, '\n')
		}
		if err := os.WriteFile(path, contents, 0o644); err != nil {
			return nil, nil, err
		}
	}
	return records, controller.Value{"truncated_tail": truncated, "preserved_records": len(records)}, nil
}

func appendJournal(path string, record controller.Value) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer file.Close()
	data, _ := json.Marshal(record)
	if _, err := file.Write(append(data, '\n')); err != nil {
		return err
	}
	return file.Sync()
}

func object(value any) controller.Value {
	if result, ok := value.(controller.Value); ok {
		return result
	}
	if result, ok := value.(map[string]any); ok {
		return result
	}
	return controller.Value{}
}

func commitControlPlane(endpoint string, owner string, state controller.Value, lost bool) (int, error) {
	body, _ := json.Marshal(controller.Value{
		"owner_token":                 owner,
		"state":                       state,
		"control_plane_response_lost": lost,
	})
	resp, err := http.Post(strings.TrimRight(endpoint, "/")+"/v1/commit", "application/json", bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	return resp.StatusCode, nil
}

func writeError(outPath string, err error) {
	result := controller.Value{"valid": false, "error": err.Error()}
	if outPath != "" {
		_ = atomicWrite(outPath, result)
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
	prior := controller.Value{}
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
	_, repair, err := repairJournal(*journalPath)
	if err != nil {
		writeError(*outPath, err)
	}
	var result controller.Value
	if command == "validate" {
		if err := controller.ValidateConfig(config); err != nil {
			writeError(*outPath, err)
		}
		result = controller.Value{"valid": true, "schema_version": config["schema_version"], "environment": config["environment"], "journal_repair": repair}
	} else {
		result, err = controller.Render(config, prior)
		if err != nil {
			writeError(*outPath, err)
		}
		result["journal_repair"] = repair
		if command == "apply" {
			owner := ""
			if rollout := object(config["rollout"]); rollout != nil {
				owner, _ = rollout["owner_token"].(string)
			}
			lost, _ := result["control_plane_response_lost"].(bool)
			status, commitErr := commitControlPlane(*controlPlane, owner, result, lost)
			if commitErr != nil {
				writeError(*outPath, commitErr)
			}
			if status != http.StatusOK && status != http.StatusServiceUnavailable {
				writeError(*outPath, fmt.Errorf("control plane commit failed with status %d", status))
			}
			if err := atomicWrite(*statePath, result); err != nil {
				writeError(*outPath, err)
			}
			outputs := object(result["outputs"])
			release := object(result["release_identity"])
			refresh := object(object(result["autoscaling_group"])["instance_refresh"])
			if err := appendJournal(*journalPath, controller.Value{
				"operation_id":            outputs["rollout_operation_id"],
				"release_manifest_sha256": release["manifest_sha256"],
				"refresh_status":          refresh["status"],
				"state_digest":            result["state_digest"],
			}); err != nil {
				writeError(*outPath, err)
			}
			if lost || status == http.StatusServiceUnavailable {
				if *outPath != "" {
					_ = atomicWrite(*outPath, result)
				}
				os.Exit(3)
			}
		}
	}
	if *outPath != "" {
		if err := atomicWrite(*outPath, result); err != nil {
			writeError(*outPath, err)
		}
	} else {
		data, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(data))
	}
}
