package provider

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

const (
	minimumMutationTimeout = time.Second
	maximumMutationTimeout = time.Hour
	maximumInventorySize    = 4 << 20
)

type runtimePreflightReport struct {
	InventoryPath  string
	InventoryBytes int64
	InventoryHosts int
	InventoryGroups []string
	BinaryRequest  string
	BinaryPath     string
	TempDir        string
	TempParent     string
	Timeout        time.Duration
}

func validateRuntimePreflight(rt *ansibleRuntime.Config) (runtimePreflightReport, error) {
	report := runtimePreflightReport{}
	if rt == nil {
		return report, errors.New("runtime configuration is required")
	}

	inventoryPath, inventoryInfo, inventorySummary, err := inspectConfiguredInventory(rt.Inventory)
	if err != nil {
		return report, err
	}
	report.InventoryPath = inventoryPath
	report.InventoryBytes = inventoryInfo.Size()
	report.InventoryHosts = inventorySummary.HostLines
	report.InventoryGroups = append([]string(nil), inventorySummary.Groups...)

	binaryPath, err := resolveAnsibleBinary(rt.AnsibleBinary)
	if err != nil {
		return report, err
	}
	report.BinaryRequest = rt.AnsibleBinary
	report.BinaryPath = binaryPath

	tempDir, tempParent, err := inspectTempWorkspace(rt.TempDir)
	if err != nil {
		return report, err
	}
	report.TempDir = tempDir
	report.TempParent = tempParent

	if err := validateMutationTimeout(rt.Timeout); err != nil {
		return report, err
	}
	report.Timeout = rt.Timeout

	return report, nil
}

func inspectConfiguredInventory(path string) (string, fs.FileInfo, ansible.InventorySummary, error) {
	var empty ansible.InventorySummary
	path = strings.TrimSpace(path)
	if path == "" {
		return "", nil, empty, errors.New("inventory path is required")
	}
	if !filepath.IsAbs(path) {
		return "", nil, empty, &pathError{field: "inventory", value: path}
	}

	cleaned := filepath.Clean(path)
	if cleaned == string(filepath.Separator) {
		return "", nil, empty, errors.New("inventory must reference a file, not the filesystem root")
	}

	info, err := os.Stat(cleaned)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return "", nil, empty, fmt.Errorf("inventory does not exist: %s", cleaned)
		}
		return "", nil, empty, fmt.Errorf("stat inventory %s: %w", cleaned, err)
	}
	if !info.Mode().IsRegular() {
		return "", nil, empty, fmt.Errorf("inventory must reference a regular file: %s", cleaned)
	}
	if info.Size() == 0 {
		return "", nil, empty, fmt.Errorf("inventory is empty: %s", cleaned)
	}
	if info.Size() > maximumInventorySize {
		return "", nil, empty, fmt.Errorf(
			"inventory %s is %d bytes; maximum supported size is %d bytes",
			cleaned,
			info.Size(),
			maximumInventorySize,
		)
	}

	summary, err := ansible.InspectInventory(cleaned)
	if err != nil {
		return "", nil, empty, err
	}
	if err := validateLocalInventorySummary(cleaned, summary); err != nil {
		return "", nil, empty, err
	}
	return cleaned, info, summary, nil
}

func validateLocalInventorySummary(path string, summary ansible.InventorySummary) error {
	if !summary.ManagedSeen {
		return fmt.Errorf("inventory %s does not define the [managed] group", path)
	}
	if summary.HostLines == 0 {
		return fmt.Errorf("inventory %s does not contain managed hosts", path)
	}
	if !summary.LocalSeen {
		return fmt.Errorf(
			"inventory %s must include localhost or 127.0.0.1 for the local managed-resource provider",
			path,
		)
	}
	return nil
}

func resolveAnsibleBinary(requested string) (string, error) {
	requested = strings.TrimSpace(requested)
	if requested == "" {
		return "", errors.New("ansible_binary is required")
	}

	resolved := requested
	if !filepath.IsAbs(requested) {
		path, err := exec.LookPath(requested)
		if err != nil {
			return "", fmt.Errorf("resolve ansible_binary %q: %w", requested, err)
		}
		resolved = path
	}

	absolute, err := filepath.Abs(resolved)
	if err != nil {
		return "", fmt.Errorf("resolve absolute ansible_binary path %q: %w", resolved, err)
	}
	absolute = filepath.Clean(absolute)

	info, err := os.Stat(absolute)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return "", fmt.Errorf("ansible_binary does not exist: %s", absolute)
		}
		return "", fmt.Errorf("stat ansible_binary %s: %w", absolute, err)
	}
	if !info.Mode().IsRegular() {
		return "", fmt.Errorf("ansible_binary must reference a regular executable file: %s", absolute)
	}
	if info.Mode().Perm()&0o111 == 0 {
		return "", fmt.Errorf("ansible_binary is not executable: %s", absolute)
	}
	return absolute, nil
}

func inspectTempWorkspace(path string) (string, string, error) {
	path = strings.TrimSpace(path)
	if path == "" {
		return "", "", errors.New("temp_dir is required")
	}
	if !filepath.IsAbs(path) {
		return "", "", &pathError{field: "temp_dir", value: path}
	}

	cleaned := filepath.Clean(path)
	if cleaned == string(filepath.Separator) {
		return "", "", errors.New("temp_dir cannot be the filesystem root")
	}

	if info, err := os.Stat(cleaned); err == nil {
		if !info.IsDir() {
			return "", "", fmt.Errorf("temp_dir exists but is not a directory: %s", cleaned)
		}
		if err := probeWritableDirectory(cleaned); err != nil {
			return "", "", fmt.Errorf("temp_dir is not usable: %w", err)
		}
		return cleaned, cleaned, nil
	} else if !errors.Is(err, fs.ErrNotExist) {
		return "", "", fmt.Errorf("stat temp_dir %s: %w", cleaned, err)
	}

	parent, err := nearestExistingDirectory(filepath.Dir(cleaned))
	if err != nil {
		return "", "", fmt.Errorf("resolve temp_dir parent for %s: %w", cleaned, err)
	}
	if err := probeWritableDirectory(parent); err != nil {
		return "", "", fmt.Errorf("temp_dir parent is not usable: %w", err)
	}
	return cleaned, parent, nil
}

func nearestExistingDirectory(path string) (string, error) {
	current := filepath.Clean(path)
	for {
		info, err := os.Stat(current)
		if err == nil {
			if !info.IsDir() {
				return "", fmt.Errorf("existing ancestor is not a directory: %s", current)
			}
			return current, nil
		}
		if !errors.Is(err, fs.ErrNotExist) {
			return "", fmt.Errorf("stat %s: %w", current, err)
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("no existing directory ancestor found for %s", path)
		}
		current = parent
	}
}

func probeWritableDirectory(directory string) error {
	probeDir, err := os.MkdirTemp(directory, ".ansibleops-preflight-")
	if err != nil {
		return fmt.Errorf("create probe directory under %s: %w", directory, err)
	}
	defer os.RemoveAll(probeDir)

	probePath := filepath.Join(probeDir, "probe")
	payload := []byte("ansibleops-runtime-preflight\n")
	if err := os.WriteFile(probePath, payload, 0o600); err != nil {
		return fmt.Errorf("write probe file under %s: %w", directory, err)
	}
	data, err := os.ReadFile(probePath)
	if err != nil {
		return fmt.Errorf("read probe file under %s: %w", directory, err)
	}
	if string(data) != string(payload) {
		return fmt.Errorf("probe file content mismatch under %s", directory)
	}
	if err := os.Remove(probePath); err != nil {
		return fmt.Errorf("remove probe file under %s: %w", directory, err)
	}
	if err := os.Remove(probeDir); err != nil {
		return fmt.Errorf("remove probe directory under %s: %w", directory, err)
	}
	return nil
}

func validateMutationTimeout(timeout time.Duration) error {
	if timeout < minimumMutationTimeout {
		return fmt.Errorf("mutation timeout must be at least %s", minimumMutationTimeout)
	}
	if timeout > maximumMutationTimeout {
		return fmt.Errorf("mutation timeout must not exceed %s", maximumMutationTimeout)
	}
	if timeout%time.Second != 0 {
		return errors.New("mutation timeout must resolve to whole seconds")
	}
	return nil
}
