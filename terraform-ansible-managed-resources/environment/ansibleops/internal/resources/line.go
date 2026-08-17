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

type lineResource struct{ rt *ansibleRuntime.Config }
type lineResourceModel struct {
	ID                  types.String `tfsdk:"id"`
	Name                types.String `tfsdk:"name"`
	Path                types.String `tfsdk:"path"`
	Line                types.String `tfsdk:"line"`
	Regexp              types.String `tfsdk:"regexp"`
	Create              types.Bool   `tfsdk:"create"`
	ObservedExactCount  types.Int64  `tfsdk:"observed_exact_count"`
	ObservedRegexpCount types.Int64  `tfsdk:"observed_regexp_count"`
}

func NewLineResource() resource.Resource { return &lineResource{} }
func (r *lineResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_line"
}
func (r *lineResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages one named line in a text file through Ansible lineinfile.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "path": schema.StringAttribute{Required: true},
		"line": schema.StringAttribute{Required: true}, "regexp": schema.StringAttribute{Optional: true}, "create": schema.BoolAttribute{Optional: true},
		"observed_exact_count": schema.Int64Attribute{Computed: true}, "observed_regexp_count": schema.Int64Attribute{Computed: true},
	}}
}
func (r *lineResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *lineResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan lineResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !requireAbsolute(stringValue(plan.Path), "path", &resp.Diagnostics) {
		return
	}
	if err := lifecycle.ValidateUnixName("line name", stringValue(plan.Name)); err != nil {
		resp.Diagnostics.AddError("Invalid line name", err.Error())
		return
	}
	if err := lifecycle.ValidateLine(stringValue(plan.Line)); err != nil {
		resp.Diagnostics.AddError("Invalid managed line", err.Error())
		return
	}
	if !execute(ctx, r.rt, ansible.LineTask("ensure managed line", stringValue(plan.Path), stringValue(plan.Line), stringValue(plan.Regexp), boolValue(plan.Create, true), "present"), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("line", stringValue(plan.Path), stringValue(plan.Name)))
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *lineResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state lineResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.LineTask("refresh managed line", stringValue(state.Path), stringValue(state.Line), stringValue(state.Regexp), boolValue(state.Create, true), "present"), &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}
	r.refresh(&state, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *lineResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan lineResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("line", stringValue(plan.Path), stringValue(plan.Name)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if !execute(ctx, r.rt, ansible.LineTask("update managed line", stringValue(plan.Path), stringValue(plan.Line), stringValue(plan.Regexp), boolValue(plan.Create, true), "present"), &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *lineResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state lineResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.LineTask("remove managed line", stringValue(state.Path), stringValue(state.Line), stringValue(state.Regexp), false, "absent"), &resp.Diagnostics)
}
func (r *lineResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("path"), req, resp)
}
func (r *lineResource) refresh(model *lineResourceModel, diagnostics interface{ AddError(string, string) }) {
	match, err := observe.InspectLine(stringValue(model.Path), stringValue(model.Line), stringValue(model.Regexp))
	if err != nil {
		diagnostics.AddError("Unable to inspect line", err.Error())
		return
	}
	if !match.Exists {
		return
	}
	model.ObservedExactCount = types.Int64Value(int64(match.ExactCount))
	model.ObservedRegexpCount = types.Int64Value(int64(match.RegexpCount))
}

var _ resource.Resource = (*lineResource)(nil)
var _ resource.ResourceWithConfigure = (*lineResource)(nil)
var _ resource.ResourceWithImportState = (*lineResource)(nil)
