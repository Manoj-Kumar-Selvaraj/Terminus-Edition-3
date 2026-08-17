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
	resp.Schema = schema.Schema{Description: "Manages a local cron entry through Ansible.", Attributes: map[string]schema.Attribute{
		"id": schema.StringAttribute{Computed: true},
		"name": schema.StringAttribute{Required: true},
		"user": schema.StringAttribute{Required: true},
		"minute": schema.StringAttribute{Optional: true},
		"hour": schema.StringAttribute{Optional: true},
		"day": schema.StringAttribute{Optional: true},
		"month": schema.StringAttribute{Optional: true},
		"weekday": schema.StringAttribute{Optional: true},
		"job": schema.StringAttribute{Required: true},
		"disabled": schema.BoolAttribute{Optional: true},
		"observed_minute": schema.StringAttribute{Computed: true},
		"observed_hour": schema.StringAttribute{Computed: true},
		"observed_day": schema.StringAttribute{Computed: true},
		"observed_month": schema.StringAttribute{Computed: true},
		"observed_weekday": schema.StringAttribute{Computed: true},
		"observed_job": schema.StringAttribute{Computed: true},
		"observed_disabled": schema.BoolAttribute{Computed: true},
	}}
}

func (r *cronResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	configure(req, resp, &r.rt)
}

func (r *cronResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan cronResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if err := lifecycle.ValidateUnixName("user", stringValue(plan.User)); err != nil {
		resp.Diagnostics.AddError("Invalid cron user", err.Error())
		return
	}
	if stringValue(plan.Name) == "" || stringValue(plan.Job) == "" {
		resp.Diagnostics.AddError("Invalid cron entry", "name and job must not be empty")
		return
	}
	if !execute(ctx, r.rt, r.task("create cron entry", plan, "present"), &resp.Diagnostics) {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("cron", stringValue(plan.User), stringValue(plan.Name), stringValue(plan.Minute), stringValue(plan.Hour), stringValue(plan.Day), stringValue(plan.Month), stringValue(plan.Weekday), stringValue(plan.Job)))
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *cronResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state cronResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	observed, err := observe.InspectCron(stringValue(state.User), stringValue(state.Name))
	if err != nil {
		resp.Diagnostics.AddError("Unable to inspect cron entry", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	applyObservedCron(&state, observed)
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *cronResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan cronResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}
	plan.ID = types.StringValue(lifecycle.ResourceIdentity("cron", stringValue(plan.User), stringValue(plan.Name), stringValue(plan.Job)))
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
	if !execute(ctx, r.rt, r.task("update cron entry", plan, "present"), &resp.Diagnostics) {
		return
	}
	r.refresh(&plan, &resp.Diagnostics)
	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *cronResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state cronResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	_ = execute(ctx, r.rt, r.task("remove cron entry", state, "absent"), &resp.Diagnostics)
}

func (r *cronResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("name"), req, resp)
}

func (r *cronResource) task(name string, model cronResourceModel, state string) ansible.Task {
	return ansible.CronTask(
		name,
		stringValue(model.Name),
		stringValue(model.User),
		stringValue(model.Minute),
		stringValue(model.Hour),
		stringValue(model.Day),
		stringValue(model.Month),
		stringValue(model.Weekday),
		stringValue(model.Job),
		state,
		boolValue(model.Disabled, false),
	)
}

func (r *cronResource) refresh(model *cronResourceModel, diagnostics interface{ AddError(string, string) }) {
	observed, err := observe.InspectCron(stringValue(model.User), stringValue(model.Name))
	if err != nil {
		diagnostics.AddError("Unable to inspect cron entry", err.Error())
		return
	}
	if !observed.Exists {
		return
	}
	applyObservedCron(model, observed)
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
