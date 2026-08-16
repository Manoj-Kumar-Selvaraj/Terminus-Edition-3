package runner

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"stackyard/internal/model"
	"stackyard/internal/policy"
)

// PrepareWorkDir ensures the workspace cwd exists and returns absolute path.
func PrepareWorkDir(dataDir string, ws *model.Workspace) (string, error) {
	dir := filepath.Join(dataDir, ws.ID, ws.WorkingDirectory)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return dir, nil
	}
	return abs, nil
}

// DescribeInvocation returns a human-readable argv string for logs/UI.
func DescribeInvocation(bin string, command string, hasPlan bool) string {
	args := policy.BuildTerraformArgs(command, hasPlan)
	return bin + " " + strings.Join(args, " ")
}

// ClassifyOutput decides whether stdout belongs in plan_output or apply_output.
func ClassifyOutput(command, output string) (planOut, applyOut string) {
	switch model.SuccessStatus(command) {
	case model.StatusApplied:
		return "", output
	default:
		return output, ""
	}
}

// ValidateBinary checks the terraform binary path is usable.
func ValidateBinary(path string) error {
	if path == "" {
		return fmt.Errorf("TERRAFORM_BIN empty")
	}
	st, err := os.Stat(path)
	if err != nil {
		return err
	}
	if st.IsDir() {
		return fmt.Errorf("TERRAFORM_BIN is a directory")
	}
	return nil
}
