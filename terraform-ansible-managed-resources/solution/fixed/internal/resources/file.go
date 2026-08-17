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

type fileResource struct{ rt *ansibleRuntime.Config }
type fileResourceModel struct {
	ID types.String `tfsdk:"id"`
	Path types.String `tfsdk:"path"`
	Mode types.String `tfsdk:"mode"`
	Owner types.String `tfsdk:"owner"`
	Group types.String `tfsdk:"group"`
	ObservedMode types.String `tfsdk:"observed_mode"`
	ObservedOwner types.String `tfsdk:"observed_owner"`
	ObservedGroup types.String `tfsdk:"observed_group"`
}

func NewFileResource() resource.Resource { return &fileResource{} }
func (r *fileResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) { resp.TypeName = req.ProviderTypeName + "_file" }
func (r *fileResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages a regular file through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "path": schema.StringAttribute{Required: true}, "mode": schema.StringAttribute{Optional: true},
		"owner": schema.StringAttribute{Optional: true}, "group": schema.StringAttribute{Optional: true}, "observed_mode": schema.StringAttribute{Computed: true},
		"observed_owner": schema.StringAttribute{Computed: true}, "observed_group": schema.StringAttribute{Computed: true},
	}}
}
func (r *fileResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) { configure(req, resp, &r.rt) }
func (r *fileResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan fileResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) { return }
	if mode := stringValue(plan.Mode); mode != "" { if _, err := lifecycle.NormalizeMode(mode); err != nil { resp.Diagnostics.AddError("Invalid mode", err.Error()); return } }
	if !execute(ctx, r.rt, ansible.FileTask("ensure regular file", stringValue(plan.Path), "touch", stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), false), &resp.Diagnostics) { return }
	plan.ID = types.StringValue(lifecycle.StablePathIdentity("file", stringValue(plan.Path)))
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *fileResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state fileResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectPath(stringValue(state.Path), false)
	if err != nil { resp.Diagnostics.AddError("Unable to inspect file", err.Error()); return }
	if !observed.Exists || observed.Kind != "file" { resp.State.RemoveResource(ctx); return }
	if !state.Mode.IsNull() && !state.Mode.IsUnknown() { state.Mode = types.StringValue(observed.Mode) }
	if !state.Owner.IsNull() && !state.Owner.IsUnknown() { state.Owner = types.StringValue(observed.Owner) }
	if !state.Group.IsNull() && !state.Group.IsUnknown() { state.Group = types.StringValue(observed.Group) }
	state.ObservedMode = types.StringValue(observed.Mode)
	state.ObservedOwner = types.StringValue(observed.Owner)
	state.ObservedGroup = types.StringValue(observed.Group)
	state.ID = types.StringValue(lifecycle.StablePathIdentity("file", stringValue(state.Path)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *fileResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior fileResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	resp.Diagnostics.Append(req.State.Get(ctx, &prior)...)
	if resp.Diagnostics.HasError() { return }
	if !execute(ctx, r.rt, ansible.FileTask("update regular file", stringValue(plan.Path), "touch", stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), false), &resp.Diagnostics) { return }
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() { plan.ID = types.StringValue(lifecycle.StablePathIdentity("file", stringValue(plan.Path))) }
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *fileResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state fileResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectPath(stringValue(state.Path), false)
	if err != nil { resp.Diagnostics.AddError("Unable to inspect file", err.Error()); return }
	if !observed.Exists { return }
	if !execute(ctx, r.rt, ansible.FileTask("remove regular file", stringValue(state.Path), "absent", "", "", "", false), &resp.Diagnostics) { return }
	observed, err = observe.InspectPath(stringValue(state.Path), false)
	if err != nil { resp.Diagnostics.AddError("Unable to verify file deletion", err.Error()); return }
	if observed.Exists { resp.Diagnostics.AddError("File deletion incomplete", "managed file still exists after Ansible completed") }
}
func (r *fileResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) { resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp) }
func (r *fileResource) refreshApplied(model *fileResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	observed, err := observe.InspectPath(stringValue(model.Path), false)
	if err != nil { diagnostics.AddError("Unable to inspect file", err.Error()); return false }
	if !observed.Exists || observed.Kind != "file" { diagnostics.AddError("File not present", "Ansible completed but the managed regular file is not present"); return false }
	model.ObservedMode = types.StringValue(observed.Mode); model.ObservedOwner = types.StringValue(observed.Owner); model.ObservedGroup = types.StringValue(observed.Group)
	return true
}

var _ resource.Resource = (*fileResource)(nil)
var _ resource.ResourceWithConfigure = (*fileResource)(nil)
var _ resource.ResourceWithImportState = (*fileResource)(nil)
