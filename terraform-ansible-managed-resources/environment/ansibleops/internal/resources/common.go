package resources

import (
	"context"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

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
	result, err := ansible.Execute(ctx, rt, task)
	if err != nil {
		diagnostics.AddError("Ansible execution failed", err.Error())
		return false
	}
	_ = result
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
