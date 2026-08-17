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

type directoryResource struct{ rt *ansibleRuntime.Config }

type directoryResourceModel struct {
	ID            types.String `tfsdk:"id"`
	Path          types.String `tfsdk:"path"`
	Mode          types.String `tfsdk:"mode"`
	Owner         types.String `tfsdk:"owner"`
	Group         types.String `tfsdk:"group"`
	ObservedKind  types.String `tfsdk:"observed_kind"`
	ObservedMode  types.String `tfsdk:"observed_mode"`
	ObservedOwner types.String `tfsdk:"observed_owner"`
	ObservedGroup types.String `tfsdk:"observed_group"`
}

func NewDirectoryResource() resource.Resource { return &directoryResource{} }
func (r *directoryResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_directory"
}
func (r *directoryResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages a directory through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "path": schema.StringAttribute{Required: true}, "mode": schema.StringAttribute{Optional: true},
		"owner": schema.StringAttribute{Optional: true}, "group": schema.StringAttribute{Optional: true}, "observed_kind": schema.StringAttribute{Computed: true},
		"observed_mode": schema.StringAttribute{Computed: true}, "observed_owner": schema.StringAttribute{Computed: true}, "observed_group": schema.StringAttribute{Computed: true},
	}}
}
func (r *directoryResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *directoryResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan directoryResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) {
		return
	}
	if !execute(ctx, r.rt, ansible.FileTask("ensure directory", stringValue(plan.Path), "directory", stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), false), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("directory", stringValue(plan.Path), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)))
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *directoryResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state directoryResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectPath(stringValue(state.Path), false)
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect directory", err.Error())
		return
	}
	if pathAbsent(observed) {
		return
	}
	state.ObservedKind = types.StringValue(observed.Kind)
	state.ObservedMode = types.StringValue(observed.Mode)
	state.ObservedOwner = types.StringValue(observed.Owner)
	state.ObservedGroup = types.StringValue(observed.Group)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *directoryResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan directoryResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("directory", stringValue(plan.Path), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if !execute(ctx, r.rt, ansible.FileTask("update directory", stringValue(plan.Path), "directory", stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), false), &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *directoryResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state directoryResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.FileTask("remove directory", stringValue(state.Path), "absent", "", "", "", false), &resp.Diagnostics)
}
func (r *directoryResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp)
}
func (r *directoryResource) refresh(model *directoryResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectPath(stringValue(model.Path), false)
	if err != nil {
		diagnostics.AddError("Unable to inspect directory", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	model.ObservedKind = types.StringValue(observed.Kind)
	model.ObservedMode = types.StringValue(observed.Mode)
	model.ObservedOwner = types.StringValue(observed.Owner)
	model.ObservedGroup = types.StringValue(observed.Group)
}

var _ resource.Resource = (*directoryResource)(nil)
var _ resource.ResourceWithConfigure = (*directoryResource)(nil)
var _ resource.ResourceWithImportState = (*directoryResource)(nil)
