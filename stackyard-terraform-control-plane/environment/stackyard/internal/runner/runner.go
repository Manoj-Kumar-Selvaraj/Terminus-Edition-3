package runner

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"stackyard/internal/model"
	"stackyard/internal/policy"
	"stackyard/internal/store"
)

type Executor struct {
	Store        *store.Store
	DataDir      string
	TerraformBin string
	Audit        func(ctx context.Context, workspaceID, action, detail, actor string) error
}

func (e *Executor) WorkspaceDir(ws *model.Workspace) string {
	return filepath.Join(e.DataDir, ws.ID, ws.WorkingDirectory)
}

func (e *Executor) EnsureWorkspaceDir(ws *model.Workspace) error {
	dir := e.WorkspaceDir(ws)
	return os.MkdirAll(dir, 0o755)
}

func (e *Executor) Execute(ctx context.Context, runID string) error {
	run, err := e.Store.GetRun(ctx, runID)
	if err != nil {
		return err
	}
	ws, err := e.Store.GetWorkspace(ctx, run.WorkspaceID)
	if err != nil {
		return err
	}
	if err := e.EnsureWorkspaceDir(ws); err != nil {
		return e.fail(ctx, run, err)
	}

	from := run.Status
	run.Status = model.StatusRunning
	if err := e.Store.UpdateRun(ctx, *run); err != nil {
		return err
	}
	if e.Audit != nil {
		_ = e.Audit(ctx, run.WorkspaceID, model.AuditRunStatus, from+"->"+model.StatusRunning, "system")
	}

	vars, err := e.Store.ListVariables(ctx, run.WorkspaceID)
	if err != nil {
		return e.fail(ctx, run, err)
	}

	dir := e.WorkspaceDir(ws)
	_, planErr := os.Stat(filepath.Join(dir, "tfplan"))
	hasPlan := planErr == nil
	args := policy.BuildTerraformArgs(run.Command, hasPlan)

	cmd := exec.CommandContext(ctx, e.TerraformBin, args...)
	cmd.Dir = dir
	cmd.Env = policy.InjectVarEnv(os.Environ(), vars)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	runErr := cmd.Run()

	outText := stdout.String()
	if stderr.Len() > 0 {
		if outText != "" {
			outText += "\n"
		}
		outText += stderr.String()
	}

	from = model.StatusRunning
	if runErr != nil {
		run.Status = model.StatusErrored
		run.Error = fmt.Sprintf("%v: %s", runErr, outText)
		if err := e.Store.UpdateRun(ctx, *run); err != nil {
			return err
		}
		if e.Audit != nil {
			_ = e.Audit(ctx, run.WorkspaceID, model.AuditRunStatus, from+"->"+model.StatusErrored, "system")
		}
		return nil
	}

	success := model.SuccessStatus(run.Command)
	run.Status = success
	run.Error = ""
	if success == model.StatusApplied {
		run.ApplyOutput = outText
	} else {
		run.PlanOutput = outText
	}
	if err := e.Store.UpdateRun(ctx, *run); err != nil {
		return err
	}
	if e.Audit != nil {
		_ = e.Audit(ctx, run.WorkspaceID, model.AuditRunStatus, from+"->"+success, "system")
	}
	return nil
}

func (e *Executor) fail(ctx context.Context, run *model.Run, cause error) error {
	from := run.Status
	run.Status = model.StatusErrored
	run.Error = cause.Error()
	_ = e.Store.UpdateRun(ctx, *run)
	if e.Audit != nil {
		_ = e.Audit(ctx, run.WorkspaceID, model.AuditRunStatus, from+"->"+model.StatusErrored, "system")
	}
	return cause
}

// SleepYield is a tiny helper so async mode can yield without busy looping.
func SleepYield() {
	time.Sleep(5 * time.Millisecond)
}
