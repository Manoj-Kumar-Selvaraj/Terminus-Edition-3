package ansible

import (
	"context"
	"fmt"

	"github.com/terminus-labs/terraform-provider-ansibleops/internal/runner"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

func Execute(ctx context.Context, rt *ansibleRuntime.Config, task Task) (runner.Result, error) {
	if rt == nil {
		return runner.Result{}, fmt.Errorf("provider runtime is not configured")
	}
	if rt.Runner == nil {
		return runner.Result{}, fmt.Errorf("provider runner is not configured")
	}
	payload, err := SingleTask(task).Render()
	if err != nil {
		return runner.Result{}, fmt.Errorf("render playbook: %w", err)
	}
	return rt.Runner.Run(ctx, runner.Request{
		Binary:    rt.AnsibleBinary,
		Inventory: rt.Inventory,
		TempDir:   rt.TempDir,
		Timeout:   rt.Timeout,
		Playbook:  payload,
		Env: map[string]string{
			"ANSIBLE_NOCOLOR":           "1",
			"ANSIBLE_HOST_KEY_CHECKING": "False",
		},
	})
}
