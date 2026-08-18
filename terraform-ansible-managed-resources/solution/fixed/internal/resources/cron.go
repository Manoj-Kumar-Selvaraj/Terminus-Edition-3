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

type cronResource struct{ rt *ansibleRuntime.Config }
type cronResourceModel struct {
	ID               types.String `tfsdk:"id"`
	Name             types.String `tfsdk:"name"`
	User             types.String `tfsdk:"user"`
	Minute           types.String `tfsdk:"minute"`
	Hour             types.String `tfsdk:"hour"`
	Day              types.String `tfsdk:"day"`
	Month            types.String `tfsdk:"month"`
	Weekday          types.String `tfsdk:"weekday"`
	Job              types.String `tfsdk:"job"`
	Disabled         types.Bool   `tfsdk:"disabled"`
	ObservedMinute   types.String `tfsdk:"observed_minute"`
	ObservedHour     types.String `tfsdk:"observed_hour"`
	ObservedDay      types.String `tfsdk:"observed_day"`
	ObservedMonth    types.String `tfsdk:"observed_month"`
	ObservedWeekday  types.String `tfsdk:"observed_weekday"`
	ObservedJob      types.String `tfsdk:"observed_job"`
	ObservedDisabled types.Bool   `tfsdk:"observed_disabled"`
}

func NewCronResource() resource.Resource { return &cronResource{} }
func (r *cronResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_cron"
}
func (r *cronResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{Description: "Manages one named local cron entry through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true}, "name": schema.StringAttribute{Required: true}, "user": schema.StringAttribute{Optional: true},
		"minute": schema.StringAttribute{Optional: true}, "hour": schema.StringAttribute{Optional: true}, "day": schema.StringAttribute{Optional: true},
		"month": schema.StringAttribute{Optional: true}, "weekday": schema.StringAttribute{Optional: true}, "job": schema.StringAttribute{Required: true},
		"disabled": schema.BoolAttribute{Optional: true}, "observed_minute": schema.StringAttribute{Computed: true}, "observed_hour": schema.StringAttribute{Computed: true},
		"observed_day": schema.StringAttribute{Computed: true}, "observed_month": schema.StringAttribute{Computed: true}, "observed_weekday": schema.StringAttribute{Computed: true},
		"observed_job": schema.StringAttribute{Computed: true}, "observed_disabled": schema.BoolAttribute{Computed: true},
	}}
}
func (r *cronResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}
func cronUser(model cronResourceModel) string {
	if value := stringValue(model.User); value != "" {
		return value
	}
	return "root"
}
func (r *cronResource) task(name string, model cronResourceModel, state string) ansible.Task {
	return ansible.CronTask(name, stringValue(model.Name), cronUser(model), lifecycle.NormalizeCronPart(stringValue(model.Minute)), lifecycle.NormalizeCronPart(stringValue(model.Hour)), lifecycle.NormalizeCronPart(stringValue(model.Day)), lifecycle.NormalizeCronPart(stringValue(model.Month)), lifecycle.NormalizeCronPart(stringValue(model.Weekday)), stringValue(model.Job), state, boolValue(model.Disabled, false))
}
func validateCronModel(model cronResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	if err := lifecycle.ValidateUnixName("cron user", cronUser(model)); err != nil {
		diagnostics.AddError("Invalid cron user", err.Error())
		return false
	}
	if stringValue(model.Name) == "" {
		diagnostics.AddError("Invalid cron entry", "name must not be empty")
		return false
	}
	if stringValue(model.Job) == "" {
		diagnostics.AddError("Invalid cron entry", "job must not be empty")
		return false
	}
	return true
}
func cronModelsEquivalent(left, right cronResourceModel) bool {
	return cronUser(left) == cronUser(right) &&
		lifecycle.NormalizeCronPart(stringValue(left.Minute)) == lifecycle.NormalizeCronPart(stringValue(right.Minute)) &&
		lifecycle.NormalizeCronPart(stringValue(left.Hour)) == lifecycle.NormalizeCronPart(stringValue(right.Hour)) &&
		lifecycle.NormalizeCronPart(stringValue(left.Day)) == lifecycle.NormalizeCronPart(stringValue(right.Day)) &&
		lifecycle.NormalizeCronPart(stringValue(left.Month)) == lifecycle.NormalizeCronPart(stringValue(right.Month)) &&
		lifecycle.NormalizeCronPart(stringValue(left.Weekday)) == lifecycle.NormalizeCronPart(stringValue(right.Weekday)) &&
		sameStringValue(left.Job, right.Job) &&
		boolValue(left.Disabled, false) == boolValue(right.Disabled, false)
}
func (r *cronResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan cronResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() || !validateCronModel(plan, &resp.Diagnostics) {
		return
	}
	if !execute(ctx, r.rt, r.task("create cron entry", plan, "present"), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("cron", cronUser(plan), stringValue(plan.Name)))
	if !r.refreshApplied(&plan, &resp.Diagnostics) {
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *cronResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state cronResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectCron(cronUser(state), stringValue(state.Name))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect cron entry", err.Error())
		return
	}
	if !observed.Exists {
		resp.State.RemoveResource(ctx)
		return
	}
	if !state.User.IsNull() && !state.User.IsUnknown() {
		state.User = types.StringValue(observed.User)
	}
	if !state.Minute.IsNull() && !state.Minute.IsUnknown() {
		state.Minute = types.StringValue(observed.Minute)
	}
	if !state.Hour.IsNull() && !state.Hour.IsUnknown() {
		state.Hour = types.StringValue(observed.Hour)
	}
	if !state.Day.IsNull() && !state.Day.IsUnknown() {
		state.Day = types.StringValue(observed.Day)
	}
	if !state.Month.IsNull() && !state.Month.IsUnknown() {
		state.Month = types.StringValue(observed.Month)
	}
	if !state.Weekday.IsNull() && !state.Weekday.IsUnknown() {
		state.Weekday = types.StringValue(observed.Weekday)
	}
	state.Job = types.StringValue(observed.Job)
	if !state.Disabled.IsNull() && !state.Disabled.IsUnknown() {
		state.Disabled = types.BoolValue(observed.Disabled)
	}
	applyObservedCron(&state, observed)
	state.ID = types.StringValue(lifecycle.ResourceIdentity("cron", cronUser(state), stringValue(state.Name)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}
func (r *cronResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan, prior cronResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	resp.Diagnostics.Append(req.State.Get(ctx, &prior)...)
	if resp.Diagnostics.HasError() || !validateCronModel(plan, &resp.Diagnostics) {
		return
	}
	if !cronModelsEquivalent(plan, prior) {
		if !execute(ctx, r.rt, r.task("update cron entry", plan, "present"), &resp.Diagnostics) {
			return
		}
	}
	plan.ID = prior.ID
	if plan.ID.IsNull() || plan.ID.IsUnknown() {
		plan.ID = types.StringValue(lifecycle.ResourceIdentity("cron", cronUser(plan), stringValue(plan.Name)))
	}
	if !r.refreshApplied(&plan, &resp.Diagnostics) {
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}
func (r *cronResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state cronResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectCron(cronUser(state), stringValue(state.Name))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect cron entry", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	if !execute(ctx, r.rt, r.task("remove cron entry", state, "absent"), &resp.Diagnostics) {
		return
	}
	observed, err = observe.InspectCron(cronUser(state), stringValue(state.Name))
	if err != nil {
		resp.Diagnostics.AddError("Unable to verify cron deletion", err.Error())
		return
	}
	if observed.Exists {
		resp.Diagnostics.AddError("Cron deletion incomplete", "managed cron entry still exists after Ansible completed")
	}
}
func (r *cronResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("name"), req, resp)
}
func (r *cronResource) refreshApplied(model *cronResourceModel, diagnostics interface{ AddError(string, string) }) bool {
	observed, err := observe.InspectCron(cronUser(*model), stringValue(model.Name))
	if err != nil {
		diagnostics.AddError("Unable to inspect cron entry", err.Error())
		return false
	}
	if !observed.Exists {
		diagnostics.AddError("Cron entry not present", "Ansible completed but the managed cron entry is absent")
		return false
	}
	applyObservedCron(model, observed)
	return true
}
func applyObservedCron(model *cronResourceModel, observed observe.CronState) {
	model.ObservedMinute = types.StringValue(observed.Minute)
	model.ObservedHour = types.StringValue(observed.Hour)
	model.ObservedDay = types.StringValue(observed.Day)
	model.ObservedMonth = types.StringValue(observed.Month)
	model.ObservedWeekday = types.StringValue(observed.Weekday)
	model.ObservedJob = types.StringValue(observed.Job)
	model.ObservedDisabled = types.BoolValue(observed.Disabled)
}

var _ resource.Resource = (*cronResource)(nil)
var _ resource.ResourceWithConfigure = (*cronResource)(nil)
var _ resource.ResourceWithImportState = (*cronResource)(nil)
