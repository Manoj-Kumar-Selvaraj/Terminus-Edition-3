package policy

import (
	"errors"
	"fmt"
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
	if existingNonTerminal > 0 {
		return ErrActiveRun
	}
	if model.RequiresLock(command) && !locked {
		return ErrLockRequired
	}
	if !model.AllowedCommands[command] {
		return fmt.Errorf("unsupported command")
	}
	return nil
}

func CanDeleteWorkspace(locked bool, activeRuns int) error {
	if locked {
		return ErrWorkspaceBusy
	}
	if activeRuns > 0 {
		return ErrActiveRun
	}
	return nil
}

func CanUnlock(currentHolder, requestedHolder string) error {
	if currentHolder != requestedHolder {
		return ErrNotLockHolder
	}
	return nil
}

func CanDiscard(status string) error {
	if status != model.StatusPlanned {
		return ErrInvalidTransition
	}
	return nil
}

func CanCancel(status string) error {
	if status != model.StatusQueued && status != model.StatusRunning {
		return ErrInvalidTransition
	}
	return nil
}

func RedactVariableValue(sensitive bool, raw string) *string {
	if sensitive {
		return nil
	}
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
		return []string{"apply", "-destroy", "-input=false", "-auto-approve", "-no-color"}
	default:
		return []string{command}
	}
}

func InjectVarEnv(base []string, vars []model.Variable) []string {
	out := append([]string{}, base...)
	for _, v := range vars {
		val := v.RawValue
		if val == "" && v.Value != nil {
			val = *v.Value
		}
		switch v.Category {
		case model.CategoryTerraform:
			out = append(out, "TF_VAR_"+v.Key+"="+val)
		case model.CategoryEnv:
			out = append(out, v.Key+"="+val)
		}
	}
	return out
}
