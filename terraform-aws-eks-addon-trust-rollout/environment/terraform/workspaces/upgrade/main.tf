locals {
  cluster_snapshot      = jsondecode(file("/app/data/cluster_snapshot.json"))
  compatibility_matrix  = jsondecode(file("/app/data/compatibility_matrix.json"))
  trust_observations    = jsondecode(file("/app/data/trust_observations.json"))
  regulated_policy      = jsondecode(file("/app/data/regulated_policy.json"))
  defaults              = jsondecode(file("/app/data/defaults.json"))
}

module "upgrade" {
  source = "../../modules/upgrade"

  cluster_snapshot     = local.cluster_snapshot
  compatibility_matrix = local.compatibility_matrix
  trust_observations   = local.trust_observations
  regulated_policy     = local.regulated_policy
  defaults             = local.defaults
}
