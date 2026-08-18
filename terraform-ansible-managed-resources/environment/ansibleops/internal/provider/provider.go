package provider

import (
	"context"
	"time"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-log/tflog"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/resources"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

type ansibleOpsProvider struct {
	version string
}

func New(version string) func() provider.Provider {
	return func() provider.Provider {
		return &ansibleOpsProvider{version: version}
	}
}

func (p *ansibleOpsProvider) Metadata(_ context.Context, _ provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "ansibleops"
	resp.Version = p.version
}

func (p *ansibleOpsProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Ansible-backed managed operating-system resources.",
		Attributes: map[string]schema.Attribute{
			"inventory": schema.StringAttribute{
				Optional:    true,
				Description: "Path to an Ansible inventory. The default inventory targets localhost.",
			},
			"ansible_binary": schema.StringAttribute{
				Optional:    true,
				Description: "ansible-playbook executable path or name.",
			},
			"timeout_seconds": schema.Int64Attribute{
				Optional:    true,
				Description: "Maximum time allowed for one Ansible mutation.",
			},
			"temp_dir": schema.StringAttribute{
				Optional:    true,
				Description: "Directory used for generated ephemeral playbooks.",
			},
		},
	}
}

func (p *ansibleOpsProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var model providerModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &model)...)
	if resp.Diagnostics.HasError() {
		return
	}

	rt := ansibleRuntime.Default()
	applyString := func(v types.String, target *string) {
		if !v.IsNull() && !v.IsUnknown() && v.ValueString() != "" {
			*target = v.ValueString()
		}
	}
	applyString(model.Inventory, &rt.Inventory)
	applyString(model.AnsibleBinary, &rt.AnsibleBinary)
	applyString(model.TempDir, &rt.TempDir)
	if !model.Timeout.IsNull() && !model.Timeout.IsUnknown() {
		seconds := model.Timeout.ValueInt64()
		if seconds <= 0 || seconds > 3600 {
			resp.Diagnostics.AddError("Invalid timeout_seconds", "timeout_seconds must be between 1 and 3600")
			return
		}
		rt.Timeout = time.Duration(seconds) * time.Second
	}

	report, err := validateRuntimePreflight(rt)
	if err != nil {
		resp.Diagnostics.AddError("Invalid provider configuration", err.Error())
		return
	}

	tflog.Info(ctx, "configured ansibleops provider", map[string]any{
		"inventory":        report.InventoryPath,
		"inventory_bytes":  report.InventoryBytes,
		"inventory_hosts":  report.InventoryHosts,
		"inventory_groups": report.InventoryGroups,
		"binary":           report.BinaryRequest,
		"binary_path":      report.BinaryPath,
		"temp_dir":         report.TempDir,
		"temp_parent":      report.TempParent,
		"timeout":          report.Timeout.String(),
	})
	resp.ResourceData = rt
	resp.DataSourceData = rt
}

type pathError struct {
	field string
	value string
}

func (e *pathError) Error() string { return e.field + " must be an absolute path: " + e.value }

func (p *ansibleOpsProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		resources.NewFileResource,
		resources.NewDirectoryResource,
		resources.NewCopyResource,
		resources.NewTemplateResource,
		resources.NewLineResource,
		resources.NewBlockResource,
		resources.NewSymlinkResource,
		resources.NewUserResource,
		resources.NewGroupResource,
		resources.NewCronResource,
	}
}

func (p *ansibleOpsProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return nil
}

var _ provider.Provider = (*ansibleOpsProvider)(nil)
