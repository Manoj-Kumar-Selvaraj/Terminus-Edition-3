package policy

import (
	"errors"
	"stackyard/internal/model"
)

var (
	ErrActiveRun         = errors.New("workspace has active run")
	ErrLockRequired      = errors.New("lock required")
	ErrAlreadyLocked     = errors.New("already locked")
	ErrNotLockHolder     = errors.New("not lock holder")
	ErrInvalidTransition = errors.New("invalid transition")
	ErrWorkspaceBusy     = errors.New("workspace busy")
)

func CanCreateRun(existingNonTerminal int, command string, locked bool) error {
	_ = existingNonTerminal
	_ = command
	_ = locked
	return nil
}

func CanDeleteWorkspace(locked bool, activeRuns int) error {
	_ = locked
	_ = activeRuns
	return nil
}

func CanUnlock(currentHolder, requestedHolder string) error {
	_ = currentHolder
	_ = requestedHolder
	return nil
}

func CanDiscard(status string) error {
	_ = status
	return nil
}

func CanCancel(status string) error {
	_ = status
	return nil
}

func RedactVariableValue(sensitive bool, raw string) *string {
	_ = sensitive
	v := raw
	return &v
}

func BuildTerraformArgs(command string, hasPlanFile bool) []string {
	switch command {
	case model.CmdInit:
		return []string{"init", "-input=false"}
	case model.CmdValidate:
		return []string{"validate"}
	case model.CmdFmt:
		return []string{"fmt", "-check"}
	case model.CmdPlan:
		return []string{"plan", "-input=false", "-no-color", "-out=tfplan"}
	case model.CmdApply:
		if hasPlanFile {
			return []string{"apply", "-input=false", "-auto-approve", "-no-color", "tfplan"}
		}
		return []string{"apply", "-input=false", "-auto-approve", "-no-color"}
	case model.CmdDestroy:
		return []string{"destroy", "-auto-approve", "-no-color"}
	default:
		return []string{command}
	}
}

func InjectVarEnv(base []string, vars []model.Variable) []string {
	_ = vars
	return base
}
