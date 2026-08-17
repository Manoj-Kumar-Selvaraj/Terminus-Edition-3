package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"catalog/internal/engine"
	"catalog/internal/paths"
	"catalog/internal/policy"
	"catalog/internal/store"
)

func Main() int {
	args := os.Args[1:]
	parsed, err := parseArgs(args)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return policy.ExitUsage
	}
	if parsed.Reset {
		if err := resetOutOnly(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	}
	st := store.New()
	switch parsed.Command {
	case "commit":
		if parsed.Input == "" {
			fmt.Fprintln(os.Stderr, "commit requires --input")
			return policy.ExitUsage
		}
		if err := engine.Commit(st, parsed.Input); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "decode":
		if err := engine.Decode(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "apply":
		if err := engine.Apply(st, parsed.CDC); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "recover":
		if err := engine.Recover(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "checkpoint":
		if err := engine.Checkpoint(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "inspect":
		if err := engine.Inspect(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "empty-check":
		if err := engine.EmptyCheck(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	default:
		fmt.Fprintln(os.Stderr, "unknown command")
		return policy.ExitUsage
	}
	return policy.ExitOK
}

type parsedArgs struct {
	Command string
	Input   string
	CDC     string
	Reset   bool
}

func parseArgs(args []string) (parsedArgs, error) {
	out := parsedArgs{}
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch a {
		case "--reset-output":
			out.Reset = true
		case "--input":
			if i+1 >= len(args) || isFlag(args[i+1]) {
				return parsedArgs{}, fmt.Errorf("commit requires --input")
			}
			i++
			out.Input = args[i]
		case "--cdc":
			if i+1 >= len(args) || isFlag(args[i+1]) {
				return parsedArgs{}, fmt.Errorf("apply --cdc requires a path")
			}
			i++
			out.CDC = args[i]
		case "--help":
			return parsedArgs{}, fmt.Errorf("%s", policy.Usage())
		default:
			if isFlag(a) {
				return parsedArgs{}, fmt.Errorf("unknown flag: %s", a)
			}
			if out.Command != "" {
				return parsedArgs{}, fmt.Errorf("unknown command: %s", a)
			}
			if !policy.KnownCommand(a) {
				return parsedArgs{}, fmt.Errorf("unknown command: %s", a)
			}
			out.Command = a
		}
	}
	if out.Command == "" {
		return parsedArgs{}, fmt.Errorf("%s", policy.Usage())
	}
	return out, nil
}

func isFlag(s string) bool {
	return len(s) > 0 && s[0] == '-'
}

func resetOutOnly() error {
	dir := paths.Out()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	for _, e := range entries {
		if err := os.RemoveAll(filepath.Join(dir, e.Name())); err != nil {
			return err
		}
	}
	return nil
}
