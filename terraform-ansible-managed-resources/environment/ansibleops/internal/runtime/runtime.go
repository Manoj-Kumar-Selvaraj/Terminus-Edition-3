package runtime

import (
	"time"

	"github.com/terminus-labs/terraform-provider-ansibleops/internal/runner"
)

type Config struct {
	Inventory     string
	AnsibleBinary string
	Timeout       time.Duration
	TempDir       string
	Runner        runner.Runner
}

func Default() *Config {
	return &Config{
		Inventory:     "/app/provider/config/inventory.ini",
		AnsibleBinary: "ansible-playbook",
		Timeout:       30 * time.Second,
		TempDir:       "/tmp/ansibleops",
		Runner:        runner.NewProcessRunner(),
	}
}
