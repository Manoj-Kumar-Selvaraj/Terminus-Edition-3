# Downstream consumer — must keep planning against legacy module outputs.
# Do not edit this workspace to invent new output names; fix the module.

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

locals {
  expected_vpc_id                      = module.network.vpc_id
  expected_private_subnet_ids          = module.network.private_subnet_ids
  expected_endpoint_security_group_ids = module.network.endpoint_security_group_ids
  expected_gateway_endpoint_ids        = module.network.gateway_vpc_endpoint_ids
  expected_interface_endpoint_ids      = module.network.interface_vpc_endpoint_ids
  expected_network                     = module.network.network
  expected_endpoint_ids                = module.network.endpoint_ids
}

output "consumer_ok" {
  value = {
    vpc_id       = local.expected_vpc_id
    private      = local.expected_private_subnet_ids
    gateway      = local.expected_gateway_endpoint_ids
    interface    = local.expected_interface_endpoint_ids
    network      = local.expected_network
    endpoints    = local.expected_endpoint_ids
    endpoint_sgs = local.expected_endpoint_security_group_ids
  }
}
