package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log/slog"
	"os"
	"time"

	"edge-router/internal/bootstrap"
	"edge-router/internal/config"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "validate":
		err = validateCommand(os.Args[2:])
	case "serve":
		err = serveCommand(os.Args[2:])
	case "print-normalized":
		err = printNormalizedCommand(os.Args[2:])
	case "help", "-h", "--help":
		usage()
		return
	default:
		usage()
		err = fmt.Errorf("unknown command %q", os.Args[1])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "edge-router-runtime:", err)
		os.Exit(1)
	}
}

func validateCommand(args []string) error {
	set := flag.NewFlagSet("validate", flag.ContinueOnError)
	configPath := set.String("config", "", "configuration path")
	if err := set.Parse(args); err != nil {
		return err
	}
	if *configPath == "" {
		return fmt.Errorf("--config is required")
	}
	app, err := bootstrap.New(bootstrap.Options{
		ConfigPath: *configPath,
		StateDir: os.TempDir() + "/edge-router-validation-state",
		ListenAddr: "127.0.0.1:0",
		AdminAddr: "127.0.0.1:0",
		LogLevel: slog.LevelError,
	})
	if err != nil {
		return err
	}
	if err := app.ValidateConfig(); err != nil {
		return err
	}
	fmt.Println("configuration valid")
	return nil
}

func serveCommand(args []string) error {
	set := flag.NewFlagSet("serve", flag.ContinueOnError)
	configPath := set.String("config", "", "configuration path")
	stateDir := set.String("state-dir", "/var/lib/edge-router", "checkpoint state directory")
	listen := set.String("listen", ":8080", "public HTTP listen address")
	admin := set.String("admin-listen", "127.0.0.1:9901", "admin HTTP listen address")
	logLevel := set.String("log-level", "info", "debug|info|warn|error")
	if err := set.Parse(args); err != nil {
		return err
	}
	if *configPath == "" {
		return fmt.Errorf("--config is required")
	}
	level, err := parseLevel(*logLevel)
	if err != nil {
		return err
	}
	app, err := bootstrap.New(bootstrap.Options{
		ConfigPath: *configPath,
		StateDir: *stateDir,
		ListenAddr: *listen,
		AdminAddr: *admin,
		LogLevel: level,
	})
	if err != nil {
		return err
	}
	root := context.Background()
	if err := app.Start(root); err != nil {
		return err
	}
	return app.WaitForSignal(root)
}

func printNormalizedCommand(args []string) error {
	set := flag.NewFlagSet("print-normalized", flag.ContinueOnError)
	configPath := set.String("config", "", "configuration path")
	if err := set.Parse(args); err != nil {
		return err
	}
	if *configPath == "" {
		return fmt.Errorf("--config is required")
	}
	state, err := config.ParseFile(*configPath)
	if err != nil {
		return err
	}
	validation := config.Validate(state)
	if err := config.ValidationErrors(validation); err != nil {
		return err
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	return encoder.Encode(validation.State)
}

func parseLevel(value string) (slog.Level, error) {
	switch value {
	case "debug":
		return slog.LevelDebug, nil
	case "info":
		return slog.LevelInfo, nil
	case "warn":
		return slog.LevelWarn, nil
	case "error":
		return slog.LevelError, nil
	default:
		return slog.LevelInfo, fmt.Errorf("invalid log level %q", value)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage:")
	fmt.Fprintln(os.Stderr, "  edge-router-runtime validate --config <path>")
	fmt.Fprintln(os.Stderr, "  edge-router-runtime serve --config <path> --state-dir <dir> --listen <addr> --admin-listen <addr>")
	fmt.Fprintln(os.Stderr, "  edge-router-runtime print-normalized --config <path>")
	fmt.Fprintln(os.Stderr, "")
	fmt.Fprintln(os.Stderr, "serve starts the public data plane and local operator/admin plane")
	fmt.Fprintln(os.Stderr, "shutdown is graceful on SIGINT or SIGTERM")
	_ = time.Second
}
