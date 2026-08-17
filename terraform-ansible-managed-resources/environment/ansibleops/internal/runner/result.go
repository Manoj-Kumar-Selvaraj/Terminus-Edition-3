package runner

import "time"

type Result struct {
	Stdout       string
	Stderr       string
	ExitCode     int
	Duration     time.Duration
	PlaybookPath string
	Command      []string
}

func (r Result) Successful() bool { return r.ExitCode == 0 }
