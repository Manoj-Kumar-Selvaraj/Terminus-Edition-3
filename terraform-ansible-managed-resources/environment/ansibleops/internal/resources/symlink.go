package resources

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/lifecycle"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

type symlinkResource struct{ rt *ansibleRuntime.Config }
type symlinkResourceModel struct {
	ID             types.String `tfsdk:"id"`
	Path           types.String `tfsdk:"path"`
	Target         types.String `tfsdk:"target"`
	Force          types.Bool   `tfsdk:"force"`
	ObservedTarget types.String `tfsdk:"observed_target"`
	ObservedKind   types.String `tfsdk:"observed_kind"`
}

func NewSymlinkResource() resource.Resource { return &symlinkResource{} }
func (r *symlinkResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_symlink"
}
func (r *symlinkResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages a symbolic link through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "path": schema.StringAttribute{Required: true}, "target": schema.StringAttribute{Required: true},
		"force": schema.BoolAttribute{Optional: true}, "observed_target": schema.StringAttribute{Computed: true}, "observed_kind": schema.StringAttribute{Computed: true},
	}}
}
func (r *symlinkResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *symlinkResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan symlinkResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) {
		return
	}
	task := ansible.FileTask("ensure symbolic link", stringValue(plan.Path), "link", "", "", "", boolValue(plan.Force, false))
	task.Args["src"] = stringValue(plan.Target)
	if !execute(ctx, r.rt, task, &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("symlink", stringValue(plan.Path), stringValue(plan.Target)))
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *symlinkResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state symlinkResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectPath(stringValue(state.Path), false)
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect symlink", err.Error())
		return
	}
	if pathAbsent(observed) {
		return
	}
	state.ObservedKind = types.StringValue(observed.Kind)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *symlinkResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan symlinkResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("symlink", stringValue(plan.Path), stringValue(plan.Target)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	task := ansible.FileTask("update symbolic link", stringValue(plan.Path), "link", "", "", "", boolValue(plan.Force, false))
	task.Args["src"] = stringValue(plan.Target)
	if !execute(ctx, r.rt, task, &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *symlinkResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state symlinkResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.FileTask("remove symbolic link", stringValue(state.Path), "absent", "", "", "", false), &resp.Diagnostics)
}
func (r *symlinkResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp)
}
func (r *symlinkResource) refresh(model *symlinkResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectPath(stringValue(model.Path), false)
	if err != nil {
		diagnostics.AddError("Unable to inspect symlink", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	model.ObservedKind = types.StringValue(observed.Kind)
	model.ObservedTarget = types.StringValue(observed.LinkTarget)
}

var _ resource.Resource = (*symlinkResource)(nil)
var _ resource.ResourceWithConfigure = (*symlinkResource)(nil)
var _ resource.ResourceWithImportState = (*symlinkResource)(nil)
