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

type copyResource struct{ rt *ansibleRuntime.Config }
type copyResourceModel struct {
	ID                types.String `tfsdk:"id"`
	Source            types.String `tfsdk:"source"`
	Destination       types.String `tfsdk:"destination"`
	Mode              types.String `tfsdk:"mode"`
	Owner             types.String `tfsdk:"owner"`
	Group             types.String `tfsdk:"group"`
	SourceDigest      types.String `tfsdk:"source_digest"`
	DestinationDigest types.String `tfsdk:"destination_digest"`
	ObservedMode      types.String `tfsdk:"observed_mode"`
}

func NewCopyResource() resource.Resource { return &copyResource{} }
func (r *copyResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_copy"
}
func (r *copyResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Copies a local source file to a managed destination through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "source": schema.StringAttribute{Required: true}, "source_digest": schema.StringAttribute{Required: true},
		"destination": schema.StringAttribute{Required: true}, "mode": schema.StringAttribute{Optional: true}, "owner": schema.StringAttribute{Optional: true},
		"group": schema.StringAttribute{Optional: true}, "destination_digest": schema.StringAttribute{Computed: true}, "observed_mode": schema.StringAttribute{Computed: true},
	}}
}
func (r *copyResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *copyResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan copyResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if !requireAbsolute(stringValue(plan.Source), "source", &resp.Diagnostics) || !requireAbsolute(stringValue(plan.Destination), "destination", &resp.Diagnostics) {
		return
	}
	if !execute(ctx, r.rt, ansible.CopyTask("copy managed file", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("copy", stringValue(plan.Destination), stringValue(plan.Source), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)))
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *copyResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state copyResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectPath(stringValue(state.Destination), true)
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect copied file", err.Error())
		return
	}
	if pathAbsent(observed) {
		return
	}
	state.ObservedMode = types.StringValue(observed.Mode)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *copyResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan copyResourceModel
	var prior copyResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	resp.Diagnostics.Append(req.State.Get(ctx, &prior)...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("copy", stringValue(plan.Destination), stringValue(plan.Source), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if stringValue(prior.Source) == stringValue(plan.Source) && stringValue(prior.Destination) == stringValue(plan.Destination) && stringValue(prior.Mode) == stringValue(plan.Mode) && stringValue(prior.Owner) == stringValue(plan.Owner) && stringValue(prior.Group) == stringValue(plan.Group) {
		return
	}
	if !execute(ctx, r.rt, ansible.CopyTask("update managed copy", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group)), &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *copyResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state copyResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.FileTask("remove copied destination", stringValue(state.Destination), "absent", "", "", "", false), &resp.Diagnostics)
}
func (r *copyResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("destination"), req, resp)
}
func (r *copyResource) refresh(model *copyResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectPath(stringValue(model.Destination), true)
	if err != nil {
		diagnostics.AddError("Unable to inspect copied file", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	model.DestinationDigest = types.StringValue(observed.Digest)
	model.ObservedMode = types.StringValue(observed.Mode)
}

var _ resource.Resource = (*copyResource)(nil)
var _ resource.ResourceWithConfigure = (*copyResource)(nil)
var _ resource.ResourceWithImportState = (*copyResource)(nil)
