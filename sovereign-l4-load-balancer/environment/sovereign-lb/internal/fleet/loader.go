package fleet

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type NodeProfile struct {
	NodeID         string `json:"node_id"`
	SessionID      string `json:"session_id"`
	Zone           string `json:"zone"`
	ControlHost    string `json:"control_host"`
	ControlPort    int    `json:"control_port"`
	StatusAddress  string `json:"status_address"`
	StateRoot      string `json:"state_root"`
	MaxFrameBytes  int    `json:"max_frame_bytes"`
	MaxConnections int    `json:"max_connections"`
}

func LoadNodeProfile(path string) (NodeProfile, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return NodeProfile{}, err
	}
	var profile NodeProfile
	if err := json.Unmarshal(data, &profile); err != nil {
		return NodeProfile{}, fmt.Errorf("decode node profile: %w", err)
	}
	return profile, ValidateNodeProfile(profile)
}

func ValidateNodeProfile(profile NodeProfile) error {
	if profile.NodeID == "" || profile.SessionID == "" || profile.Zone == "" {
		return fmt.Errorf("node identity is incomplete")
	}
	if profile.ControlHost == "" || profile.ControlPort < 1 || profile.ControlPort > 65535 {
		return fmt.Errorf("control endpoint is invalid")
	}
	if profile.StatusAddress == "" {
		return fmt.Errorf("status address is required")
	}
	if profile.StateRoot == "" {
		return fmt.Errorf("state root is required")
	}
	if profile.MaxFrameBytes < 4096 {
		return fmt.Errorf("max_frame_bytes is too small")
	}
	if profile.MaxConnections < 1 {
		return fmt.Errorf("max_connections must be positive")
	}
	return nil
}

func EnsureNodeStateRoot(profile NodeProfile) error {
	return os.MkdirAll(profile.StateRoot, 0750)
}

func LoadAllProfiles(root string, inventory Inventory) (map[string]NodeProfile, error) {
	result := map[string]NodeProfile{}
	for _, node := range inventory.Nodes {
		path := inventory.NodeConfigPath(root, node.ID)
		profile, err := LoadNodeProfile(path)
		if err != nil {
			return nil, fmt.Errorf("node %q: %w", node.ID, err)
		}
		if profile.NodeID != node.ID {
			return nil, fmt.Errorf("node profile %q has mismatched node_id %q", path, profile.NodeID)
		}
		if profile.Zone != node.Zone {
			return nil, fmt.Errorf("node %q profile zone %q does not match inventory zone %q", node.ID, profile.Zone, node.Zone)
		}
		result[node.ID] = profile
	}
	return result, nil
}

func WriteNodeProfile(path string, profile NodeProfile) error {
	if err := ValidateNodeProfile(profile); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0750); err != nil {
		return err
	}
	data, err := json.MarshalIndent(profile, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0640)
}
