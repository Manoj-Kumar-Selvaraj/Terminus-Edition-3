package provider

import "github.com/hashicorp/terraform-plugin-framework/types"

type providerModel struct {
	Inventory     types.String `tfsdk:"inventory"`
	AnsibleBinary types.String `tfsdk:"ansible_binary"`
	Timeout       types.Int64  `tfsdk:"timeout_seconds"`
	TempDir       types.String `tfsdk:"temp_dir"`
}
