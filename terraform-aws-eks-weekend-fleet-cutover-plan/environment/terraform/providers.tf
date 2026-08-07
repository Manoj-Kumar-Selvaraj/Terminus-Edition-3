# Credential-less providers. The fleet design is rendered as a plan on a build
# host that has no AWS credentials and no reachable Kubernetes API server, so
# every provider is pinned to static placeholders and every remote-lookup
# shortcut is disabled.

provider "aws" {
  region = var.region

  access_key = "AKIAOFFLINEPLANNER00"
  secret_key = "offline-planner-secret-key-not-a-real-credential"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
}

provider "kubernetes" {
  config_path = "${path.root}/kubeconfig.plan.yaml"
}

provider "helm" {
  kubernetes {
    config_path = "${path.root}/kubeconfig.plan.yaml"
  }
}
