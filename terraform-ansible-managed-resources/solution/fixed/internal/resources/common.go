package resources

import (
	"context"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/lifecycle"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

var ownershipRegistry = struct {
	sync.Mutex
	keys map[string]struct{}
}{keys: map[string]struct{}{}}

func configure(req resource.ConfigureRequest, resp *resource.ConfigureResponse, target **ansibleRuntime.Config) {
	if req.ProviderData == nil {
		return
	}
	rt, ok := req.ProviderData.(*ansibleRuntime.Config)
	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected provider data type",
			fmt.Sprintf("expected *runtime.Config, got %T", req.ProviderData),
		)
		return
	}
	*target = rt
}

func execute(ctx context.Context, rt *ansibleRuntime.Config, task ansible.Task, diagnostics *diag.Diagnostics) bool {
	key, create, remove := taskOwnership(task)
	if create && key != "" && !claimOwnership(key) {
		diagnostics.AddError(
			"Duplicate external ownership",
			"another Terraform resource in this provider process already owns "+key,
		)
		return false
	}

	result, err := ansible.Execute(ctx, rt, task)
	if err != nil {
		if create && key != "" {
			releaseOwnership(key)
		}
		diagnostics.AddError("Ansible execution failed", err.Error())
		return false
	}
	_ = result
	if remove && key != "" {
		releaseOwnership(key)
	}
	return true
}

func taskOwnership(task ansible.Task) (key string, create bool, remove bool) {
	arg := func(name string) string {
		value, _ := task.Args[name].(string)
		return value
	}
	switch task.Name {
	case "ensure regular file", "ensure directory", "ensure symbolic link":
		return "path:" + arg("path"), true, false
	case "copy managed file", "render managed template":
		return "path:" + arg("dest"), true, false
	case "ensure local user":
		return "user:" + arg("name"), true, false
	case "ensure local group":
		return "group:" + arg("name"), true, false
	case "create cron entry":
		return "cron:" + arg("user") + ":" + arg("name"), true, false
	case "remove regular file", "remove directory", "remove symbolic link":
		return "path:" + arg("path"), false, true
	case "remove copied destination", "remove template destination":
		return "path:" + arg("path"), false, true
	case "remove local user":
		return "user:" + arg("name"), false, true
	case "remove local group":
		return "group:" + arg("name"), false, true
	case "remove cron entry":
		return "cron:" + arg("user") + ":" + arg("name"), false, true
	default:
		return "", false, false
	}
}

func claimOwnership(key string) bool {
	ownershipRegistry.Lock()
	defer ownershipRegistry.Unlock()
	if _, exists := ownershipRegistry.keys[key]; exists {
		return false
	}
	ownershipRegistry.keys[key] = struct{}{}
	return true
}

func releaseOwnership(key string) {
	ownershipRegistry.Lock()
	delete(ownershipRegistry.keys, key)
	ownershipRegistry.Unlock()
}

func sameStringValue(left, right types.String) bool {
	if left.IsUnknown() || right.IsUnknown() {
		return left.IsUnknown() && right.IsUnknown()
	}
	if left.IsNull() || right.IsNull() {
		return left.IsNull() && right.IsNull()
	}
	return left.ValueString() == right.ValueString()
}

func sameBoolValue(left, right types.Bool) bool {
	if left.IsUnknown() || right.IsUnknown() {
		return left.IsUnknown() && right.IsUnknown()
	}
	if left.IsNull() || right.IsNull() {
		return left.IsNull() && right.IsNull()
	}
	return left.ValueBool() == right.ValueBool()
}

func sameInt64Value(left, right types.Int64) bool {
	if left.IsUnknown() || right.IsUnknown() {
		return left.IsUnknown() && right.IsUnknown()
	}
	if left.IsNull() || right.IsNull() {
		return left.IsNull() && right.IsNull()
	}
	return left.ValueInt64() == right.ValueInt64()
}

func sameModeValue(left, right types.String) bool {
	if left.IsUnknown() || right.IsUnknown() {
		return left.IsUnknown() && right.IsUnknown()
	}
	if left.IsNull() || right.IsNull() {
		return left.IsNull() && right.IsNull()
	}
	return lifecycle.ModeEqual(left.ValueString(), right.ValueString())
}

func sameStringSlice(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func requireAbsolute(pathValue, field string, diagnostics *diag.Diagnostics) bool {
	if strings.TrimSpace(pathValue) == "" {
		diagnostics.AddError("Missing path", field+" must not be empty")
		return false
	}
	if !filepath.IsAbs(pathValue) {
		diagnostics.AddError("Path must be absolute", field+" must be an absolute path")
		return false
	}
	return true
}

func stringValue(value types.String) string {
	if value.IsNull() || value.IsUnknown() {
		return ""
	}
	return value.ValueString()
}

func boolValue(value types.Bool, fallback bool) bool {
	if value.IsNull() || value.IsUnknown() {
		return fallback
	}
	return value.ValueBool()
}

func int64Value(value types.Int64) int64 {
	if value.IsNull() || value.IsUnknown() {
		return 0
	}
	return value.ValueInt64()
}

func int64Text(value types.Int64) string {
	if value.IsNull() || value.IsUnknown() {
		return ""
	}
	return strconv.FormatInt(value.ValueInt64(), 10)
}

func boolText(value types.Bool, fallback bool) string {
	return strconv.FormatBool(boolValue(value, fallback))
}

func listStrings(ctx context.Context, value types.List, diagnostics *diag.Diagnostics) []string {
	if value.IsNull() || value.IsUnknown() {
		return nil
	}
	var out []string
	diagnostics.Append(value.ElementsAs(ctx, &out, false)...)
	return out
}

func mapStrings(ctx context.Context, value types.Map, diagnostics *diag.Diagnostics) map[string]string {
	if value.IsNull() || value.IsUnknown() {
		return nil
	}
	var out map[string]string
	diagnostics.Append(value.ElementsAs(ctx, &out, false)...)
	return out
}

func pathAbsent(observed observe.PathState) bool {
	return !observed.Exists
}

func stringListValue(ctx context.Context, values []string, diagnostics *diag.Diagnostics) types.List {
	result, diags := types.ListValueFrom(ctx, types.StringType, values)
	diagnostics.Append(diags...)
	return result
}
