locals {
  desired = jsondecode(file("/app/data/desired.json"))
}

module "vpc" {
  source  = "../../modules/vpc"
  desired = local.desired
}

output "private_app_route_table_ids" {
  value = module.vpc.private_app_route_table_ids
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
