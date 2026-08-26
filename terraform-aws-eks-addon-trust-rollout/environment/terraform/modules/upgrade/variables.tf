# Variables for EKS add-on trust rollout upgrade module

variable "cluster_snapshot" {
  description = "Current snapshot dataset of the EKS cluster"
  type        = any
}

variable "compatibility_matrix" {
  description = "Target add-on compatibility matrix and prerequisite rollout graph"
  type        = any
}

variable "trust_observations" {
  description = "Required IRSA service account subjects and forbidden subject definitions"
  type        = any
}

variable "regulated_policy" {
  description = "Placement requirements and capacity constraints for regulated workloads"
  type        = any
}

variable "defaults" {
  description = "Cluster defaults, OIDC provider configuration, and system taint settings"
  type        = any
}
