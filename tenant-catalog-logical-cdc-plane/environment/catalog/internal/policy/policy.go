package policy

import "catalog/internal/model"

const (
	StatusActive = "ACTIVE"
	StatusFrozen = "FROZEN"
	CDCSourceWAL = "wal"
	ExitOK       = 0
	ExitUsage    = 2
)

var Commands = []string{
	"commit", "decode", "apply", "recover", "checkpoint", "inspect", "empty-check",
}

var KnownFlags = map[string]bool{
	"--input":        true,
	"--cdc":          true,
	"--reset-output": true,
	"--help":         true,
}

func KnownCommand(name string) bool {
	for _, c := range Commands {
		if c == name {
			return true
		}
	}
	return false
}

func MutationOpOK(op string) bool {
	return op == "insert" || op == "update" || op == "delete"
}

func TenantFrozen(status string) bool {
	return status == StatusFrozen
}

func Tables() []string {
	return append([]string{}, model.Tables...)
}

func Usage() string {
	return "usage: catalogctl [--reset-output] <commit|decode|apply|recover|checkpoint|inspect|empty-check> [--input PATH] [--cdc PATH]"
}
