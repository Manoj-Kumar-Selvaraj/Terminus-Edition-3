# Frozen root. The whole weekend fleet is rendered by the module below; this
# file only forwards the inventory into it.

module "eks_weekend_fleet" {
  source = "./modules/eks_weekend_fleet"

  region                     = var.region
  account_id                 = var.account_id
  resource_prefix            = var.resource_prefix
  cluster_name               = var.cluster_name
  kubernetes_version         = var.kubernetes_version
  vpc_id                     = var.vpc_id
  private_subnet_ids         = var.private_subnet_ids
  cluster_security_group_id  = var.cluster_security_group_id
  oidc_provider_arn          = var.oidc_provider_arn
  oidc_provider_url          = var.oidc_provider_url
  cluster_log_types          = var.cluster_log_types
  cluster_log_retention_days = var.cluster_log_retention_days
  node_groups                = var.node_groups
  cluster_addons             = var.cluster_addons
  irsa_roles                 = var.irsa_roles
  helm_releases              = var.helm_releases
  artifactory                = var.artifactory
  monitoring                 = var.monitoring
  weekend_schedule           = var.weekend_schedule
  ingress                    = var.ingress
  tags                       = var.tags

  chart_root = "${path.root}/charts"
}
