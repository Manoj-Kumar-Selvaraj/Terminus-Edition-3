package resources

import (
	"context"
	"regexp"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/ansible"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/lifecycle"
	"github.com/terminus-labs/terraform-provider-ansibleops/internal/observe"
	ansibleRuntime "github.com/terminus-labs/terraform-provider-ansibleops/internal/runtime"
)

type lineResource struct{ rt *ansibleRuntime.Config }
type lineResourceModel struct {
	ID types.String `tfsdk:"id"`
	Name types.String `tfsdk:"name"`
	Path types.String `tfsdk:"path"`
	Line types.String `tfsdk:"line"`
	Regexp types.String `tfsdk:"regexp"`
	Create types.Bool `tfsdk:"create"`
	ObservedExactCount types.Int64 `tfsdk:"observed_exact_count"`
	ObservedRegexpCount types.Int64 `tfsdk:"observed_regexp_count"`
}

func NewLineResource() resource.Resource { return &lineResource{} }
func (r *lineResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) { resp.TypeName = req.ProviderTypeName + "_line" }
func (r *lineResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages one named line in a text file through Ansible lineinfile.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "path": schema.StringAttribute{Required: true},
		"line": schema.StringAttribute{Required: true}, "regexp": schema.StringAttribute{Optional: true}, "create": schema.BoolAttribute{Optional: true},
		"observed_exact_count": schema.Int64Attribute{Computed: true}, "observed_regexp_count": schema.Int64Attribute{Computed: true},
	}}
}
func (r *lineResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) { configure(req, resp, &r.rt) }
func validateLineModel(model lineResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	if err := lifecycle.ValidateUnixName("line name", stringValue(model.Name)); err != nil { diagnostics.AddError("Invalid line name", err.Error()); return false }
	if err := lifecycle.ValidateLine(stringValue(model.Line)); err != nil { diagnostics.AddError("Invalid managed line", err.Error()); return false }
	if expression := stringValue(model.Regexp); expression != "" { if _, err := regexp.Compile(expression); err != nil { diagnostics.AddError("Invalid line regexp", err.Error()); return false } }
	return true
}
func (r *lineResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan lineResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) || !validateLineModel(plan, &resp.Diagnostics) { return }
	if !execute(ctx, r.rt, ansible.LineTask("ensure managed line", stringValue(plan.Path), stringValue(plan.Line), stringValue(plan.Regexp), boolValue(plan.Create, true), "present"), &resp.Diagnostics) { return }
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("line", stringValue(plan.Path), stringValue(plan.Name)))
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *lineResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state lineResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...); if resp.Diagnostics.HasError() { return }
	match, err := observe.InspectLine(stringValue(state.Path), stringValue(state.Line), stringValue(state.Regexp))
	if err != nil { resp.Diagnostics.AddError("Unable to inspect line", err.Error()); return }
	if !match.Exists || match.ExactCount != 1 { resp.State.RemoveResource(ctx); return }
	state.ObservedExactCount = types.Int64Value(int64(match.ExactCount)); state.ObservedRegexpCount = types.Int64Value(int64(match.RegexpCount))
	state.ID = types.StringValue(lifecycle.ResourceIdentity("line", stringValue(state.Path), stringValue(state.Name)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *lineResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior lineResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...); resp.Diagnostics.Append(req.State.Get(ctx, &prior)...); if resp.Diagnostics.HasError() { return }
	if !validateLineModel(plan, &resp.Diagnostics) { return }
	expression := stringValue(plan.Regexp)
	if expression == "" && stringValue(prior.Line) != stringValue(plan.Line) { expression = "^" + regexp.QuoteMeta(stringValue(prior.Line)) + "$" }
	if !execute(ctx, r.rt, ansible.LineTask("update managed line", stringValue(plan.Path), stringValue(plan.Line), expression, boolValue(plan.Create, true), "present"), &resp.Diagnostics) { return }
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() { plan.ID = types.StringValue(lifecycle.ResourceIdentity("line", stringValue(plan.Path), stringValue(plan.Name))) }
	if !r.refreshApplied(&plan, &resp.Diagnostics) { return }
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *lineResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state lineResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...); if resp.Diagnostics.HasError() { return }
	match, err := observe.InspectLine(stringValue(state.Path), stringValue(state.Line), "")
	if err != nil { resp.Diagnostics.AddError("Unable to inspect line", err.Error()); return }
	if !match.Exists || match.ExactCount == 0 { return }
	if !execute(ctx, r.rt, ansible.LineTask("remove managed line", stringValue(state.Path), stringValue(state.Line), "", false, "absent"), &resp.Diagnostics) { return }
	match, err = observe.InspectLine(stringValue(state.Path), stringValue(state.Line), "")
	if err != nil { resp.Diagnostics.AddError("Unable to verify line deletion", err.Error()); return }
	if match.ExactCount != 0 { resp.Diagnostics.AddError("Line deletion incomplete", "managed line still exists after Ansible completed") }
}
func (r *lineResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) { resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp) }
func (r *lineResource) refreshApplied(model *lineResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	match, err := observe.InspectLine(stringValue(model.Path), stringValue(model.Line), stringValue(model.Regexp))
	if err != nil { diagnostics.AddError("Unable to inspect line", err.Error()); return false }
	if !match.Exists || match.ExactCount != 1 { diagnostics.AddError("Line not converged", "Ansible completed but the managed line contract is not satisfied exactly once"); return false }
	model.ObservedExactCount = types.Int64Value(int64(match.ExactCount)); model.ObservedRegexpCount = types.Int64Value(int64(match.RegexpCount)); return true
}

var _ resource.Resource = (*lineResource)(nil)
var _ resource.ResourceWithConfigure = (*lineResource)(nil)
var _ resource.ResourceWithImportState = (*lineResource)(nil)
