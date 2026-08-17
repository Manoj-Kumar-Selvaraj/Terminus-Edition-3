package resources

import (
	"context"
	"fmt"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/lifecycle"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

type blockResource struct{ rt *ansibleRuntime.Config }
type blockResourceModel struct {
	ID       types.String `tfsdk:"id"`
	Name     types.String `tfsdk:"name"`
	Path     types.String `tfsdk:"path"`
	Block    types.String `tfsdk:"block"`
	Marker   types.String `tfsdk:"marker"`
	Create   types.Bool   `tfsdk:"create"`
	Observed types.Bool   `tfsdk:"observed"`
}

func NewBlockResource() resource.Resource { return &blockResource{} }
func (r *blockResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_block"
}
func (r *blockResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages one named marked text block through Ansible blockinfile.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "path": schema.StringAttribute{Required: true},
		"block": schema.StringAttribute{Required: true}, "marker": schema.StringAttribute{Optional: true, Computed: true}, "create": schema.BoolAttribute{Optional: true}, "observed": schema.BoolAttribute{Computed: true},
	}}
}
func (r *blockResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func blockMarker(model blockResourceModel) string {
	if marker := stringValue(model.Marker); marker != "" {
		return marker
	}
	return fmt.Sprintf("# {mark} ANSIBLEOPS %s", stringValue(model.Name))
}
func validateBlockModel(model blockResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	if err := lifecycle.ValidateUnixName("block name", stringValue(model.Name)); err != nil {
		diagnostics.AddError("Invalid block name", err.Error())
		return false
	}
	if err := lifecycle.ValidateBlockMarker(blockMarker(model)); err != nil {
		diagnostics.AddError("Invalid block marker", err.Error())
		return false
	}
	return true
}
func (r *blockResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan blockResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) || !validateBlockModel(plan, &resp.Diagnostics) {
		return
	}
	marker := blockMarker(plan)
	if !execute(ctx, r.rt, ansible.BlockTask("ensure managed block", stringValue(plan.Path), stringValue(plan.Block), marker, boolValue(plan.Create, true), "present"), &resp.Diagnostics) {
		return
	}
	plan.Marker = types.StringValue(marker)
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("block", stringValue(plan.Path), stringValue(plan.Name)))
	if !r.refreshApplied(&plan, &resp.Diagnostics) {
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *blockResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state blockResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	match, err := observe.InspectBlock(stringValue(state.Path), stringValue(state.Block), stringValue(state.Marker))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect block", err.Error())
		return
	}
	if !match.Exists || !match.BlockFound {
		resp.State.RemoveResource(ctx)
		return
	}
	state.Observed = types.BoolValue(true)
	state.ID = types.StringValue(lifecycle.ResourceIdentity("block", stringValue(state.Path), stringValue(state.Name)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *blockResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior blockResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	resp.Diagnostics.Append(req.State.Get(ctx, &prior)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if !validateBlockModel(plan, &resp.Diagnostics) {
		return
	}
	marker := blockMarker(plan)
	if !execute(ctx, r.rt, ansible.BlockTask("update managed block", stringValue(plan.Path), stringValue(plan.Block), marker, boolValue(plan.Create, true), "present"), &resp.Diagnostics) {
		return
	}
	plan.Marker = types.StringValue(marker)
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() {
		plan.ID = types.StringValue(lifecycle.ResourceIdentity("block", stringValue(plan.Path), stringValue(plan.Name)))
	}
	if !r.refreshApplied(&plan, &resp.Diagnostics) {
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *blockResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state blockResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	match, err := observe.InspectBlock(stringValue(state.Path), stringValue(state.Block), stringValue(state.Marker))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect block", err.Error())
		return
	}
	if !match.Exists || !match.BlockFound {
		return
	}
	if !execute(ctx, r.rt, ansible.BlockTask("remove managed block", stringValue(state.Path), stringValue(state.Block), stringValue(state.Marker), false, "absent"), &resp.Diagnostics) {
		return
	}
	match, err = observe.InspectBlock(stringValue(state.Path), stringValue(state.Block), stringValue(state.Marker))
	if err != nil {
		resp.Diagnostics.AddError("Unable to verify block deletion", err.Error())
		return
	}
	if match.BlockFound {
		resp.Diagnostics.AddError("Block deletion incomplete", "managed block still exists after Ansible completed")
	}
}
func (r *blockResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp)
}
func (r *blockResource) refreshApplied(model *blockResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	match, err := observe.InspectBlock(stringValue(model.Path), stringValue(model.Block), stringValue(model.Marker))
	if err != nil {
		diagnostics.AddError("Unable to inspect block", err.Error())
		return false
	}
	if !match.Exists || !match.BlockFound {
		diagnostics.AddError("Block not converged", "Ansible completed but the named managed block is not present")
		return false
	}
	model.Observed = types.BoolValue(true)
	return true
}

var _ resource.Resource = (*blockResource)(nil)
var _ resource.ResourceWithConfigure = (*blockResource)(nil)
var _ resource.ResourceWithImportState = (*blockResource)(nil)
