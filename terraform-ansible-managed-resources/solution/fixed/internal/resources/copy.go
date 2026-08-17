package resources

import (
	"context"
	"strings"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/lifecycle"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

type copyResource struct{ rt *ansibleRuntime.Config }
type copyResourceModel struct {
	ID types.String `tfsdk:"id"`
	Source types.String `tfsdk:"source"`
	Destination types.String `tfsdk:"destination"`
	Mode types.String `tfsdk:"mode"`
	Owner types.String `tfsdk:"owner"`
	Group types.String `tfsdk:"group"`
	SourceDigest types.String `tfsdk:"source_digest"`
	DestinationDigest types.String `tfsdk:"destination_digest"`
	ObservedMode types.String `tfsdk:"observed_mode"`
}

func NewCopyResource() resource.Resource { return &copyResource{} }
func (r *copyResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) { resp.TypeName = req.ProviderTypeName + "_copy" }
func (r *copyResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Copies a local source file to a managed destination through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "source": schema.StringAttribute{Required: true}, "source_digest": schema.StringAttribute{Required: true},
		"destination": schema.StringAttribute{Required: true}, "mode": schema.StringAttribute{Optional: true}, "owner": schema.StringAttribute{Optional: true},
		"group": schema.StringAttribute{Optional: true}, "destination_digest": schema.StringAttribute{Computed: true}, "observed_mode": schema.StringAttribute{Computed: true},
	}}
}
func (r *copyResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) { configure(req, resp, &r.rt) }
func validateCopySource(model copyResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	actual, err := lifecycle.FileDigest(stringValue(model.Source))
	if err != nil { diagnostics.AddError("Unable to hash copy source", err.Error()); return false }
	if !strings.EqualFold(actual, stringValue(model.SourceDigest)) { diagnostics.AddError("Copy source digest mismatch", "source_digest does not match the current source file content"); return false }
	return true
}
func (r *copyResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan copyResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() { return }
	if !requireAbsolute(stringValue(plan.Source), "source", &resp.Diagnostics) || !requireAbsolute(stringValue(plan.Destination), "destination", &resp.Diagnostics) { return }
	if !validateCopySource(plan, &resp.Diagnostics) { return }
	if !execute(ctx, r.rt, ansible.CopyTask("copy managed file", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)), &resp.Diagnostics) { return }
	plan.ID = types.StringValue(lifecycle.StablePathIdentity("copy", stringValue(plan.Destination)))
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *copyResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state copyResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectPath(stringValue(state.Destination), true)
	if err != nil { resp.Diagnostics.AddError("Unable to inspect copied file", err.Error()); return }
	if !observed.Exists || observed.Kind != "file" { resp.State.RemoveResource(ctx); return }
	state.SourceDigest = types.StringValue(observed.Digest)
	state.DestinationDigest = types.StringValue(observed.Digest)
	if !state.Mode.IsNull() && !state.Mode.IsUnknown() { state.Mode = types.StringValue(observed.Mode) }
	state.ObservedMode = types.StringValue(observed.Mode)
	state.ID = types.StringValue(lifecycle.StablePathIdentity("copy", stringValue(state.Destination)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *copyResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior copyResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...); resp.Diagnostics.Append(req.State.Get(ctx, &prior)...)
	if resp.Diagnostics.HasError() { return }
	if !validateCopySource(plan, &resp.Diagnostics) { return }
	if !execute(ctx, r.rt, ansible.CopyTask("update managed copy", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)), &resp.Diagnostics) { return }
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() { plan.ID = types.StringValue(lifecycle.StablePathIdentity("copy", stringValue(plan.Destination))) }
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *copyResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state copyResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() { return }
	observed, err := observe.InspectPath(stringValue(state.Destination), false)
	if err != nil { resp.Diagnostics.AddError("Unable to inspect copied file", err.Error()); return }
	if !observed.Exists { return }
	if !execute(ctx, r.rt, ansible.FileTask("remove copied destination", stringValue(state.Destination), "absent", "", "", "", false), &resp.Diagnostics) { return }
	observed, err = observe.InspectPath(stringValue(state.Destination), false)
	if err != nil { resp.Diagnostics.AddError("Unable to verify copied file deletion", err.Error()); return }
	if observed.Exists { resp.Diagnostics.AddError("Copy deletion incomplete", "managed destination still exists after Ansible completed") }
}
func (r *copyResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) { resource.ImportStatePassthroughID(ctx, path.Root("destination"), req, resp) }
func (r *copyResource) refreshApplied(model *copyResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	observed, err := observe.InspectPath(stringValue(model.Destination), true)
	if err != nil { diagnostics.AddError("Unable to inspect copied file", err.Error()); return false }
	if !observed.Exists || observed.Kind != "file" { diagnostics.AddError("Copy destination not present", "Ansible completed but the managed destination is not a regular file"); return false }
	model.DestinationDigest = types.StringValue(observed.Digest); model.ObservedMode = types.StringValue(observed.Mode)
	return true
}

var _ resource.Resource = (*copyResource)(nil)
var _ resource.ResourceWithConfigure = (*copyResource)(nil)
var _ resource.ResourceWithImportState = (*copyResource)(nil)
