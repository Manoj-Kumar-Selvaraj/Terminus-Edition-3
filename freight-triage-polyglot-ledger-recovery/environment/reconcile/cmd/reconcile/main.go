// Command reconcile matches intake events against the native freight ledger.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"freight/reconcile/internal/audit"
	"freight/reconcile/internal/model"
	"freight/reconcile/internal/report"
	"freight/reconcile/internal/selftest"
)

func usage() {
	fmt.Println("freight-reconcile - intake to ledger reconciliation")
	fmt.Println()
	fmt.Println("usage:")
	fmt.Println("  reconcile run [--root DIR] [--snapshot FILE] [--journal FILE]")
	fmt.Println("                [--out-report FILE] [--out-csv FILE]")
	fmt.Println("  reconcile selftest [--out FILE]")
	fmt.Println("  reconcile version")
}

func runReconcile(argv []string) int {
	flags := flag.NewFlagSet("run", flag.ContinueOnError)
	root := flags.String("root", "/app", "application root")
	snapshotPath := flags.String("snapshot", "", "ledger snapshot path")
	journalPath := flags.String("journal", "", "intake journal path")
	registryPath := flags.String("registry", "", "lane registry path")
	outReport := flags.String("out-report", "", "audit report path")
	outCSV := flags.String("out-csv", "", "audit ledger csv path")
	if err := flags.Parse(argv); err != nil {
		return 1
	}
	if *snapshotPath == "" {
		*snapshotPath = filepath.Join(*root, "output", "ledger-snapshot.json")
	}
	if *journalPath == "" {
		*journalPath = filepath.Join(*root, "output", "intake-journal.json")
	}
	if *registryPath == "" {
		*registryPath = filepath.Join(*root, "environment", "data", "registry", "lanes.json")
	}
	if *outReport == "" {
		*outReport = filepath.Join(*root, "output", "audit-report.json")
	}
	if *outCSV == "" {
		*outCSV = filepath.Join(*root, "output", "audit-ledger.csv")
	}

	snapshot, err := model.LoadSnapshot(*snapshotPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 2
	}
	journal, err := model.LoadJournal(*journalPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 2
	}
	lanes, err := model.LoadLaneRegistry(*registryPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 2
	}

	result := audit.Reconcile(snapshot, journal, lanes)
	csvBytes, err := report.RenderCSV(result.Rows)
	if err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 3
	}
	if err := report.WriteFile(*outCSV, csvBytes); err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 3
	}
	document := report.Build(snapshot, journal, result, csvBytes)
	if err := report.WriteJSON(*outReport, document); err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 3
	}
	fmt.Printf("reconcile: rows=%d orphans=%d report=%s\n",
		len(result.Rows), len(result.Orphans), *outReport)
	return 0
}

func runSelftest(argv []string) int {
	flags := flag.NewFlagSet("selftest", flag.ContinueOnError)
	root := flags.String("root", "/app", "application root")
	out := flags.String("out", "", "selftest report path")
	if err := flags.Parse(argv); err != nil {
		return 1
	}
	if *out == "" {
		*out = filepath.Join(*root, "output", "selftest-go.json")
	}
	document := selftest.Build()
	if err := report.WriteJSON(*out, document); err != nil {
		fmt.Fprintln(os.Stderr, "reconcile:", err)
		return 3
	}
	fmt.Printf("reconcile: selftest digest=%v\n", document["digest"])
	return 0
}

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}
	switch os.Args[1] {
	case "run":
		os.Exit(runReconcile(os.Args[2:]))
	case "selftest":
		os.Exit(runSelftest(os.Args[2:]))
	case "version":
		fmt.Println("freight-reconcile freight-audit/2")
	default:
		usage()
		os.Exit(1)
	}
}
