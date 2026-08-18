package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"catalog/internal/engine"
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/policy"
	"catalog/internal/store"
	"catalog/internal/txn"
)

func Main() int {
	st := store.New()
	txnID, lsn, err := txn.NextIDs(st)
	if err == nil {
		_ = st.AppendWAL(model.WalRecord{LSN: lsn, TxnID: txnID, Kind: "BEGIN", Epoch: 3})
	}
	args := os.Args[1:]
	reset := false
	cmd := ""
	input := ""
	cdcPath := ""
	unknown := false
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch a {
		case "--reset-output":
			reset = true
		case "--input":
			if i+1 < len(args) {
				i++
				input = args[i]
			}
		case "--cdc":
			if i+1 < len(args) {
				i++
				cdcPath = args[i]
			}
		case "commit", "decode", "apply", "recover", "checkpoint", "inspect", "empty-check":
			cmd = a
		default:
			if len(a) > 0 && a[0] == '-' {
				unknown = true
			} else if cmd == "" {
				unknown = true
				cmd = a
			}
		}
	}
	if reset {
		_ = os.WriteFile(paths.WAL(), []byte{}, 0o644)
		_ = clearOut()
	}
	if unknown || cmd == "" {
		fmt.Fprintln(os.Stderr, policy.Usage())
		return 2
	}
	switch cmd {
	case "commit":
		if input == "" {
			input = os.DevNull
		}
		if err := engine.Commit(st, input); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "decode":
		if err := engine.Decode(st); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
	case "apply":
		if err := engine.Apply(st, cdcPath); err != nil {
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
		return 2
	}
	return 0
}

func clearOut() error {
	entries, err := os.ReadDir(paths.Out())
	if err != nil {
		return nil
	}
	for _, e := range entries {
		_ = os.RemoveAll(filepath.Join(paths.Out(), e.Name()))
	}
	return nil
}
