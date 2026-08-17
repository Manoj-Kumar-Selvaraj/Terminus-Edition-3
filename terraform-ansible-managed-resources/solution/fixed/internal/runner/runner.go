package runner

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type Request struct {
	Binary    string
	Inventory string
	TempDir   string
	Timeout   time.Duration
	Playbook  []byte
	Env       map[string]string
}

type Runner interface {
	Run(context.Context, Request) (Result, error)
}

type ProcessRunner struct{}

func NewProcessRunner() *ProcessRunner { return &ProcessRunner{} }

func (r *ProcessRunner) Run(ctx context.Context, req Request) (Result, error) {
	started := time.Now()
	if err := validateRequest(req); err != nil {
		return Result{}, err
	}
	if err := os.MkdirAll(req.TempDir, 0o700); err != nil {
		return Result{}, fmt.Errorf("create temp directory: %w", err)
	}

	f, err := os.CreateTemp(req.TempDir, "ansibleops-*.yml")
	if err != nil {
		return Result{}, fmt.Errorf("create temporary playbook: %w", err)
	}
	playbookPath := f.Name()
	defer os.Remove(playbookPath)

	if _, err := f.Write(req.Playbook); err != nil {
		_ = f.Close()
		return Result{PlaybookPath: playbookPath}, fmt.Errorf("write temporary playbook: %w", err)
	}
	if err := f.Close(); err != nil {
		return Result{PlaybookPath: playbookPath}, fmt.Errorf("close temporary playbook: %w", err)
	}

	commandCtx, cancel := context.WithTimeout(ctx, req.Timeout)
	defer cancel()

	argv := []string{req.Binary, "-i", req.Inventory, playbookPath}
	cmd := exec.CommandContext(commandCtx, req.Binary, "-i", req.Inventory, playbookPath)
	cmd.Env = mergeEnv(os.Environ(), req.Env)

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	runErr := cmd.Run()

	result := Result{
		Stdout:       stdout.String(),
		Stderr:       stderr.String(),
		ExitCode:     exitCode(runErr),
		Duration:     time.Since(started),
		PlaybookPath: playbookPath,
		Command:      argv,
	}
	if runErr == nil {
		return result, nil
	}
	if errors.Is(commandCtx.Err(), context.DeadlineExceeded) {
		return result, fmt.Errorf("ansible execution exceeded %s", req.Timeout)
	}
	if errors.Is(commandCtx.Err(), context.Canceled) {
		return result, fmt.Errorf("ansible execution canceled: %w", commandCtx.Err())
	}
	var exitErr *exec.ExitError
	if errors.As(runErr, &exitErr) {
		return result, fmt.Errorf("ansible-playbook exited with code %d: %s", exitErr.ExitCode(), bounded(stderr.String(), 2048))
	}
	return result, fmt.Errorf("start ansible-playbook: %w", runErr)
}

func validateRequest(req Request) error {
	if strings.TrimSpace(req.Binary) == "" {
		return errors.New("ansible binary is required")
	}
	if strings.ContainsRune(req.Binary, '\x00') {
		return errors.New("ansible binary contains NUL")
	}
	if strings.TrimSpace(req.Inventory) == "" {
		return errors.New("inventory is required")
	}
	if !filepath.IsAbs(req.Inventory) {
		return fmt.Errorf("inventory must be absolute: %s", req.Inventory)
	}
	if !filepath.IsAbs(req.TempDir) {
		return fmt.Errorf("temp directory must be absolute: %s", req.TempDir)
	}
	if req.Timeout <= 0 {
		return errors.New("timeout must be positive")
	}
	if len(req.Playbook) == 0 {
		return errors.New("playbook is empty")
	}
	return nil
}

func mergeEnv(base []string, overrides map[string]string) []string {
	if len(overrides) == 0 {
		return base
	}
	values := make(map[string]string, len(base)+len(overrides))
	order := make([]string, 0, len(base)+len(overrides))
	for _, item := range base {
		key, value, ok := strings.Cut(item, "=")
		if !ok {
			continue
		}
		if _, seen := values[key]; !seen {
			order = append(order, key)
		}
		values[key] = value
	}
	for key, value := range overrides {
		if _, seen := values[key]; !seen {
			order = append(order, key)
		}
		values[key] = value
	}
	result := make([]string, 0, len(values))
	for _, key := range order {
		result = append(result, key+"="+values[key])
	}
	return result
}

func exitCode(err error) int {
	if err == nil {
		return 0
	}
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) {
		return exitErr.ExitCode()
	}
	return -1
}

func bounded(value string, limit int) string {
	value = strings.TrimSpace(value)
	if len(value) <= limit {
		return value
	}
	return value[:limit] + "..."
}
