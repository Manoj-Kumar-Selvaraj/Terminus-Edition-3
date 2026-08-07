locals {
  topology = jsondecode(file("/app/data/topology.json"))
}

module "spoke" {
  source = "../../modules/spoke"

  name                            = local.topology.name
  location                        = local.topology.location
  resource_group_name             = local.topology.resource_group_name
  vnet_address_space              = local.topology.vnet_address_space
  firewall_private_ip             = local.topology.firewall_private_ip
  subnets                         = local.topology.subnets
  private_endpoint_subnet_key     = local.topology.private_endpoint_subnet_key
  private_endpoints               = local.topology.private_endpoints
  application_gateway_subnet_cidr = local.topology.application_gateway_subnet_cidr
  app_ports                       = local.topology.app_ports
  log_analytics_workspace_id      = local.topology.log_analytics_workspace_id
  enable_ddos_protection          = local.topology.enable_ddos_protection
  ddos_protection_plan_id         = local.topology.ddos_protection_plan_id
  allowed_admin_cidrs             = local.topology.allowed_admin_cidrs
  tags                            = local.topology.tags
}
