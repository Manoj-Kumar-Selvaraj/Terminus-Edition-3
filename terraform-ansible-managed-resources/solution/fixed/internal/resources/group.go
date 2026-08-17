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

type groupResource struct{ rt *ansibleRuntime.Config }
type groupResourceModel struct {
	ID types.String `tfsdk:"id"`
	Name types.String `tfsdk:"name"`
	GID types.Int64 `tfsdk:"gid"`
	System types.Bool `tfsdk:"system"`
	ObservedGID types.Int64 `tfsdk:"observed_gid"`
	ObservedMembers types.List `tfsdk:"observed_members"`
}

func NewGroupResource() resource.Resource { return &groupResource{} }
func (r *groupResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) { resp.TypeName = req.ProviderTypeName + "_group" }
func (r *groupResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages a local operating-system group through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "gid": schema.Int64Attribute{Optional: true},
		"system": schema.BoolAttribute{Optional: true}, "observed_gid": schema.Int64Attribute{Computed: true}, "observed_members": schema.ListAttribute{Computed: true, ElementType: types.StringType},
	}}
}
func (r *groupResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) { configure(req, resp, &r.rt) }
func (r *groupResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan groupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...); if resp.Diagnostics.HasError() { return }
	if err := lifecycle.ValidateUnixName("group", stringValue(plan.Name)); err != nil { resp.Diagnostics.AddError("Invalid group name", err.Error()); return }
	if !execute(ctx, r.rt, ansible.GroupTask("ensure local group", stringValue(plan.Name), "present", int64Value(plan.GID), boolValue(plan.System, false)), &resp.Diagnostics) { return }
	plan.ID = types.StringValue(lifecycle.StableNameIdentity("group", stringValue(plan.Name)))
	if !r.refreshApplied(ctx, &plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *groupResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state groupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...); if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectGroup(stringValue(state.Name))
	if err != nil { resp.Diagnostics.AddError("Unable to inspect group", err.Error()); return }
	if !observed.Exists { resp.State.RemoveResource(ctx); return }
	if !state.GID.IsNull() && !state.GID.IsUnknown() { state.GID = types.Int64Value(observed.GID) }
	state.ObservedGID = types.Int64Value(observed.GID)
	state.ObservedMembers = stringListValue(ctx, observed.Members, &resp.Diagnostics)
	state.ID = types.StringValue(lifecycle.StableNameIdentity("group", stringValue(state.Name)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *groupResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior groupResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...); resp.Diagnostics.Append(req.State.Get(ctx, &prior)...); if resp.Diagnostics.HasError() { return }
	if !execute(ctx, r.rt, ansible.GroupTask("update local group", stringValue(plan.Name), "present", int64Value(plan.GID), boolValue(plan.System, false)), &resp.Diagnostics) { return }
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() { plan.ID = types.StringValue(lifecycle.StableNameIdentity("group", stringValue(plan.Name))) }
	if !r.refreshApplied(ctx, &plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *groupResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state groupResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...); if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectGroup(stringValue(state.Name))
	if err != nil { resp.Diagnostics.AddError("Unable to inspect group", err.Error()); return }
	if !observed.Exists { return }
	if !execute(ctx, r.rt, ansible.GroupTask("remove local group", stringValue(state.Name), "absent", 0, boolValue(state.System, false)), &resp.Diagnostics) { return }
	observed, err = observe.InspectGroup(stringValue(state.Name))
	if err != nil { resp.Diagnostics.AddError("Unable to verify group deletion", err.Error()); return }
	if observed.Exists { resp.Diagnostics.AddError("Group deletion incomplete", "managed group still exists after Ansible completed") }
}
func (r *groupResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) { resource.ImportStatePassthroughID(ctx, path.Root("name"), req, resp) }
func (r *groupResource) refreshApplied(ctx context.Context, model *groupResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	observed, err := observe.InspectGroup(stringValue(model.Name))
	if err != nil { diagnostics.AddError("Unable to inspect group", err.Error()); return false }
	if !observed.Exists { diagnostics.AddError("Group not present", "Ansible completed but the managed group is absent"); return false }
	model.ObservedGID = types.Int64Value(observed.GID)
	list, diags := types.ListValueFrom(ctx, types.StringType, observed.Members)
	if diags.HasError() { diagnostics.AddError("Unable to encode group members", "observed group members could not be represented") } else { model.ObservedMembers = list }
	return true
}

var _ resource.Resource = (*groupResource)(nil)
var _ resource.ResourceWithConfigure = (*groupResource)(nil)
var _ resource.ResourceWithImportState = (*groupResource)(nil)
