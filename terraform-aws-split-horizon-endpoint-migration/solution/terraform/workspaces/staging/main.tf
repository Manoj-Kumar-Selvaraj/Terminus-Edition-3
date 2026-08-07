provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}

locals {
  inventory       = jsondecode(file("/app/data/inventory.json"))
  endpoints       = jsondecode(file("/app/data/endpoints.json"))
  dns_zones       = jsondecode(file("/app/data/dns_zones.json"))
  allowed_sources = jsondecode(file("/app/data/allowed_sources.json"))
}

module "network" {
  source = "../../modules/network"

  environment     = local.inventory.environment
  inventory       = local.inventory
  endpoints       = local.endpoints
  dns_zones       = local.dns_zones
  allowed_sources = local.allowed_sources
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "vpc_cidr_block" {
  value = module.network.vpc_cidr_block
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_route_table_ids" {
  value = module.network.private_route_table_ids
}

output "public_route_table_ids" {
  value = module.network.public_route_table_ids
}

output "gateway_vpc_endpoint_ids" {
  value = module.network.gateway_vpc_endpoint_ids
}

output "interface_vpc_endpoint_ids" {
  value = module.network.interface_vpc_endpoint_ids
}

output "endpoint_security_group_id" {
  value = module.network.endpoint_security_group_id
}

output "endpoint_security_group_ids" {
  value = module.network.endpoint_security_group_ids
}

output "network" {
  value = module.network.network
}

output "endpoint_ids" {
  value = module.network.endpoint_ids
}
