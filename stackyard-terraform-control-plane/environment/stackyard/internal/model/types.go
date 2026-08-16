package model

import "time"

const (
	StatusQueued     = "queued"
	StatusRunning    = "running"
	StatusPlanned    = "planned"
	StatusApplied    = "applied"
	StatusErrored    = "errored"
	StatusDiscarded  = "discarded"
	StatusCanceled   = "canceled"

	CmdInit     = "init"
	CmdValidate = "validate"
	CmdFmt      = "fmt"
	CmdPlan     = "plan"
	CmdApply    = "apply"
	CmdDestroy  = "destroy"

	CategoryTerraform = "terraform"
	CategoryEnv       = "env"

	AuditRunCreated  = "run.created"
	AuditRunStatus   = "run.status"
	AuditLockAcquire = "lock.acquire"
	AuditLockRelease = "lock.release"
)

var TerminalStatuses = map[string]bool{
	StatusApplied:   true,
	StatusErrored:   true,
	StatusDiscarded: true,
	StatusCanceled:  true,
}

var NonTerminalStatuses = map[string]bool{
	StatusQueued:  true,
	StatusRunning: true,
	StatusPlanned: true,
}

var AllowedCommands = map[string]bool{
	CmdInit:     true,
	CmdValidate: true,
	CmdFmt:      true,
	CmdPlan:     true,
	CmdApply:    true,
	CmdDestroy:  true,
}

type Org struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Slug      string    `json:"slug"`
	CreatedAt time.Time `json:"created_at"`
}

type Workspace struct {
	ID                string    `json:"id"`
	OrgID             string    `json:"org_id"`
	Name              string    `json:"name"`
	WorkingDirectory  string    `json:"working_directory"`
	Locked            bool      `json:"locked"`
	LockID            *string   `json:"lock_id"`
	CreatedAt         time.Time `json:"created_at"`
}

type Variable struct {
	ID          string    `json:"id"`
	WorkspaceID string    `json:"workspace_id"`
	Key         string    `json:"key"`
	Value       *string   `json:"value"`
	Sensitive   bool      `json:"sensitive"`
	Category    string    `json:"category"`
	CreatedAt   time.Time `json:"created_at"`
	// RawValue is never serialized; used by runner injection.
	RawValue string `json:"-"`
}

type Run struct {
	ID           string    `json:"id"`
	WorkspaceID  string    `json:"workspace_id"`
	Command      string    `json:"command"`
	Status       string    `json:"status"`
	Message      string    `json:"message"`
	PlanOutput   string    `json:"plan_output"`
	ApplyOutput  string    `json:"apply_output"`
	Error        string    `json:"error"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type Lock struct {
	ID          string    `json:"id"`
	WorkspaceID string    `json:"workspace_id"`
	Holder      string    `json:"holder"`
	Reason      string    `json:"reason"`
	CreatedAt   time.Time `json:"created_at"`
}

type AuditEvent struct {
	ID          string    `json:"id"`
	WorkspaceID string    `json:"workspace_id"`
	Action      string    `json:"action"`
	Detail      string    `json:"detail"`
	Actor       string    `json:"actor"`
	CreatedAt   time.Time `json:"created_at"`
}

func IsTerminal(status string) bool {
	return TerminalStatuses[status]
}

func IsNonTerminal(status string) bool {
	return NonTerminalStatuses[status]
}

func RequiresLock(command string) bool {
	return command == CmdApply || command == CmdDestroy
}

func SuccessStatus(command string) string {
	switch command {
	case CmdApply, CmdDestroy:
		return StatusApplied
	default:
		return StatusPlanned
	}
}
