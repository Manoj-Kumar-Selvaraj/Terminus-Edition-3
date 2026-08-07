package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	_ "modernc.org/sqlite"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "subcommand required")
		os.Exit(1)
	}
	cmd := os.Args[1]
	fs := flag.NewFlagSet(cmd, flag.ExitOnError)
	_ = fs.String("root", "/app", "")
	jsonOut := fs.Bool("json", false, "")
	_ = fs.String("owner", "", "")
	_ = fs.String("fail-after", "", "")
	_ = fs.Parse(os.Args[2:])
	_ = jsonOut
	out := map[string]any{
		"valid":         false,
		"phase":         "ROUTE_DRIFT_UNRECOVERED",
		"feature_level": 0,
		"error":         "vpc reconciliation controller has not implemented control-plane reconciliation",
	}
	b, _ := json.MarshalIndent(out, "", "  ")
	fmt.Println(string(b))
	if cmd != "inspect" {
		os.Exit(2)
	}
}
