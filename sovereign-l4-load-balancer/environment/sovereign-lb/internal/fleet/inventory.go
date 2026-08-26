package fleet

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type NodeRecord struct {
	ID      string `json:"id"`
	Zone    string `json:"zone"`
	Control string `json:"control"`
	Status  string `json:"status"`
}

type Inventory struct {
	Nodes []NodeRecord `json:"nodes"`
}

func LoadInventory(path string) (Inventory, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Inventory{}, err
	}
	var value Inventory
	if err := json.Unmarshal(data, &value); err != nil {
		return Inventory{}, fmt.Errorf("decode fleet inventory: %w", err)
	}
	if err := ValidateInventory(value); err != nil {
		return Inventory{}, err
	}
	sort.Slice(value.Nodes, func(i, j int) bool { return value.Nodes[i].ID < value.Nodes[j].ID })
	return value, nil
}

func ValidateInventory(value Inventory) error {
	if len(value.Nodes) == 0 {
		return fmt.Errorf("fleet inventory is empty")
	}
	ids := map[string]struct{}{}
	zones := map[string]struct{}{}
	controls := map[string]struct{}{}
	statuses := map[string]struct{}{}
	for _, node := range value.Nodes {
		if node.ID == "" || node.Zone == "" || node.Control == "" || node.Status == "" {
			return fmt.Errorf("node %q has incomplete fields", node.ID)
		}
		if _, exists := ids[node.ID]; exists {
			return fmt.Errorf("duplicate node id %q", node.ID)
		}
		if _, exists := controls[node.Control]; exists {
			return fmt.Errorf("duplicate control endpoint %q", node.Control)
		}
		if _, exists := statuses[node.Status]; exists {
			return fmt.Errorf("duplicate status endpoint %q", node.Status)
		}
		if err := validateEndpoint(node.Control); err != nil {
			return fmt.Errorf("node %q control: %w", node.ID, err)
		}
		if err := validateEndpoint(node.Status); err != nil {
			return fmt.Errorf("node %q status: %w", node.ID, err)
		}
		ids[node.ID] = struct{}{}
		zones[node.Zone] = struct{}{}
		controls[node.Control] = struct{}{}
		statuses[node.Status] = struct{}{}
	}
	if len(zones) < 2 {
		return fmt.Errorf("fleet inventory must span at least two zones")
	}
	return nil
}

func validateEndpoint(value string) error {
	host, portText, ok := strings.Cut(value, ":")
	if !ok || host == "" || portText == "" {
		return fmt.Errorf("endpoint %q must be host:port", value)
	}
	port, err := strconv.Atoi(portText)
	if err != nil || port < 1 || port > 65535 {
		return fmt.Errorf("endpoint %q has invalid port", value)
	}
	return nil
}

func (inventory Inventory) ByZone(zone string) []NodeRecord {
	result := make([]NodeRecord, 0)
	for _, node := range inventory.Nodes {
		if node.Zone == zone {
			result = append(result, node)
		}
	}
	sort.Slice(result, func(i, j int) bool { return result[i].ID < result[j].ID })
	return result
}

func (inventory Inventory) NodeConfigPath(root, nodeID string) string {
	return filepath.Join(root, "config", "nodes", nodeID+".json")
}

func (inventory Inventory) Zones() []string {
	seen := map[string]struct{}{}
	for _, node := range inventory.Nodes {
		seen[node.Zone] = struct{}{}
	}
	result := make([]string, 0, len(seen))
	for zone := range seen {
		result = append(result, zone)
	}
	sort.Strings(result)
	return result
}

func (inventory Inventory) Lookup(nodeID string) (NodeRecord, bool) {
	for _, node := range inventory.Nodes {
		if node.ID == nodeID {
			return node, true
		}
	}
	return NodeRecord{}, false
}

func (inventory Inventory) ZoneQuorum(unavailableAllowance int) bool {
	zones := inventory.Zones()
	if len(zones) == 0 {
		return false
	}
	if unavailableAllowance < 0 {
		unavailableAllowance = 0
	}
	return len(zones)-unavailableAllowance >= 1
}
