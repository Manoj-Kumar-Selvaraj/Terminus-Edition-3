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

type userResource struct{ rt *ansibleRuntime.Config }
type userResourceModel struct {
	ID             types.String `tfsdk:"id"`
	Name           types.String `tfsdk:"name"`
	UID            types.Int64  `tfsdk:"uid"`
	Group          types.String `tfsdk:"group"`
	Groups         types.List   `tfsdk:"groups"`
	Shell          types.String `tfsdk:"shell"`
	Home           types.String `tfsdk:"home"`
	CreateHome     types.Bool   `tfsdk:"create_home"`
	RemoveHome     types.Bool   `tfsdk:"remove_home_on_destroy"`
	ObservedUID    types.Int64  `tfsdk:"observed_uid"`
	ObservedGID    types.Int64  `tfsdk:"observed_gid"`
	ObservedGroup  types.String `tfsdk:"observed_group"`
	ObservedGroups types.List   `tfsdk:"observed_groups"`
	ObservedShell  types.String `tfsdk:"observed_shell"`
	ObservedHome   types.String `tfsdk:"observed_home"`
}

func NewUserResource() resource.Resource { return &userResource{} }
func (r *userResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_user"
}
func (r *userResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages a local operating-system user through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "uid": schema.Int64Attribute{Optional: true},
		"group": schema.StringAttribute{Optional: true}, "groups": schema.ListAttribute{Optional: true, ElementType: types.StringType},
		"shell": schema.StringAttribute{Optional: true}, "home": schema.StringAttribute{Optional: true}, "create_home": schema.BoolAttribute{Optional: true},
		"remove_home_on_destroy": schema.BoolAttribute{Optional: true}, "observed_uid": schema.Int64Attribute{Computed: true}, "observed_gid": schema.Int64Attribute{Computed: true},
		"observed_group": schema.StringAttribute{Computed: true}, "observed_groups": schema.ListAttribute{Computed: true, ElementType: types.StringType},
		"observed_shell": schema.StringAttribute{Computed: true}, "observed_home": schema.StringAttribute{Computed: true},
	}}
}
func (r *userResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func (r *userResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan userResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if err := lifecycle.ValidateUnixName("user", stringValue(plan.Name)); err != nil {
		resp.Diagnostics.AddError("Invalid user name", err.Error())
		return
	}
	groups := lifecycle.CanonicalGroups(listStrings(ctx, plan.Groups, &resp.Diagnostics))
	if resp.Diagnostics.HasError() {
		return
	}
	if !execute(ctx, r.rt, ansible.UserTask("ensure local user", stringValue(plan.Name), "present", int64Value(plan.UID), stringValue(plan.Group), groups, stringValue(plan.Shell), stringValue(plan.Home), boolValue(plan.CreateHome, true), false), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("user", stringValue(plan.Name), int64Text(plan.UID), stringValue(plan.Group), stringValue(plan.Shell), stringValue(plan.Home)))
	r.refresh(ctx, &plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *userResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state userResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectUser(stringValue(state.Name))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect user", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	r.applyObserved(ctx, &state, observed, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *userResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan userResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	groups := lifecycle.CanonicalGroups(listStrings(ctx, plan.Groups, &resp.Diagnostics))
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("user", stringValue(plan.Name), int64Text(plan.UID), stringValue(plan.Group), stringValue(plan.Shell), stringValue(plan.Home)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if !execute(ctx, r.rt, ansible.UserTask("update local user", stringValue(plan.Name), "present", int64Value(plan.UID), stringValue(plan.Group), groups, stringValue(plan.Shell), stringValue(plan.Home), boolValue(plan.CreateHome, true), false), &resp.Diagnostics) {
		return
	}
	r.refresh(ctx, &plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *userResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state userResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, ansible.UserTask("remove local user", stringValue(state.Name), "absent", 0, "", nil, "", "", false, !boolValue(state.RemoveHome, false)), &resp.Diagnostics)
}
func (r *userResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("name"), req, resp)
}
func (r *userResource) refresh(ctx context.Context, model *userResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectUser(stringValue(model.Name))
	if err != nil {
		diagnostics.AddError("Unable to inspect user", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	model.ObservedUID = types.Int64Value(observed.UID)
	model.ObservedGID = types.Int64Value(observed.GID)
	model.ObservedGroup = types.StringValue(observed.Group)
	model.ObservedShell = types.StringValue(observed.Shell)
	model.ObservedHome = types.StringValue(observed.Home)
	list, _ := types.ListValueFrom(ctx, types.StringType, observed.Groups)
	model.ObservedGroups = list
}
func (r *userResource) applyObserved(ctx context.Context, model *userResourceModel, observed observe.UserState, diagnostics interface{ AddError(string, string) }) {
	model.ObservedUID = types.Int64Value(observed.UID)
	model.ObservedGID = types.Int64Value(observed.GID)
	model.ObservedGroup = types.StringValue(observed.Group)
	model.ObservedShell = types.StringValue(observed.Shell)
	model.ObservedHome = types.StringValue(observed.Home)
	list, diags := types.ListValueFrom(ctx, types.StringType, observed.Groups)
	if diags.HasError() {
		diagnostics.AddError("Unable to encode observed groups", "observed supplementary groups could not be represented")
	} else {
		model.ObservedGroups = list
	}
}

var _ resource.Resource = (*userResource)(nil)
var _ resource.ResourceWithConfigure = (*userResource)(nil)
var _ resource.ResourceWithImportState = (*userResource)(nil)
