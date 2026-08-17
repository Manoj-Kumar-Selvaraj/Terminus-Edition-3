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

type templateResource struct{ rt *ansibleRuntime.Config }
type templateResourceModel struct {
	ID                types.String `tfsdk:"id"`
	Source            types.String `tfsdk:"source"`
	Destination       types.String `tfsdk:"destination"`
	Mode              types.String `tfsdk:"mode"`
	Owner             types.String `tfsdk:"owner"`
	Group             types.String `tfsdk:"group"`
	Variables         types.Map    `tfsdk:"variables"`
	SourceDigest      types.String `tfsdk:"source_digest"`
	VarsFingerprint   types.String `tfsdk:"variables_fingerprint"`
	DestinationDigest types.String `tfsdk:"destination_digest"`
}

func NewTemplateResource() resource.Resource { return &templateResource{} }
func (r *templateResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_template"
}
func (r *templateResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Renders an Ansible/Jinja template to a managed destination.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "source": schema.StringAttribute{Required: true}, "destination": schema.StringAttribute{Required: true},
		"mode": schema.StringAttribute{Optional: true}, "owner": schema.StringAttribute{Optional: true}, "group": schema.StringAttribute{Optional: true},
		"variables": schema.MapAttribute{Optional: true, ElementType: types.StringType}, "source_digest": schema.StringAttribute{Computed: true},
		"variables_fingerprint": schema.StringAttribute{Computed: true}, "destination_digest": schema.StringAttribute{Computed: true},
	}}
}
func (r *templateResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *templateResource) ModifyPlan(ctx context.Context, req resource.ModifyPlanRequest, resp *resource.ModifyPlanResponse) {
	if req.Plan.Raw.IsNull() {
		return
	}
	var plan templateResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || plan.Source.IsUnknown() || plan.Source.IsNull() {
		return
	}
	vars := mapStrings(ctx, plan.Variables, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.SourceDigest = types.StringValue(lifecycle.SourceFingerprint(stringValue(plan.Source)))
	plan.VarsFingerprint = types.StringValue(lifecycle.MapFingerprint(vars))
	resp.Diagnostics.Append(resp.Plan.Set(ctx, &plan)...)
}
func (r *templateResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan templateResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if !requireAbsolute(stringValue(plan.Source), "source", &resp.Diagnostics) || !requireAbsolute(stringValue(plan.Destination), "destination", &resp.Diagnostics) {
		return
	}
	vars := mapStrings(ctx, plan.Variables, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}
	if !execute(ctx, r.rt, ansible.TemplateTask("render managed template", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), vars), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("template", stringValue(plan.Destination), stringValue(plan.Source), stringValue(plan.Mode), stringValue(plan.VarsFingerprint)))
	if plan.SourceDigest.IsNull() || plan.SourceDigest.IsUnknown() {
		plan.SourceDigest = types.StringValue(lifecycle.SourceFingerprint(stringValue(plan.Source)))
	}
	if plan.VarsFingerprint.IsNull() || plan.VarsFingerprint.IsUnknown() {
		plan.VarsFingerprint = types.StringValue(lifecycle.MapFingerprint(vars))
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *templateResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state templateResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectPath(stringValue(state.Destination), true)
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect template destination", err.Error())
		return
	}
	if pathAbsent(observed) {
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *templateResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan templateResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	vars := mapStrings(ctx, plan.Variables, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("template", stringValue(plan.Destination), stringValue(plan.Source), stringValue(plan.Mode), stringValue(plan.VarsFingerprint)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if !execute(ctx, r.rt, ansible.TemplateTask("update managed template", stringValue(plan.Source), stringValue(plan.Destination), stringValue(plan.Mode), stringValue(plan.Owner), stringValue(plan.Group), vars), &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *templateResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state templateResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.FileTask("remove template destination", stringValue(state.Destination), "absent", "", "", "", false), &resp.Diagnostics)
}
func (r *templateResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("destination"), req, resp)
}
func (r *templateResource) refresh(model *templateResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectPath(stringValue(model.Destination), true)
	if err != nil {
		diagnostics.AddError("Unable to inspect template destination", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	model.DestinationDigest = types.StringValue(observed.Digest)
}

var _ resource.Resource = (*templateResource)(nil)
var _ resource.ResourceWithConfigure = (*templateResource)(nil)
var _ resource.ResourceWithImportState = (*templateResource)(nil)
var _ resource.ResourceWithModifyPlan = (*templateResource)(nil)
