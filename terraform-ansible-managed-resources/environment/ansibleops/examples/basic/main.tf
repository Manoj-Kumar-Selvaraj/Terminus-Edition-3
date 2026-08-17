terraform {
  required_providers {
    ansibleops = {
      source  = "local/ansibleops"
      version = "0.1.0"
    }
  }
}

provider "ansibleops" {
  inventory       = "/app/provider/config/inventory.ini"
  timeout_seconds = 30
}

resource "ansibleops_directory" "smoke" {
  path = "/tmp/ansibleops-smoke-managed"
  mode = "0755"
}

resource "ansibleops_line" "config" {
  name   = "managed-flag"
  path   = "/tmp/ansibleops-smoke-managed/config.txt"
  line   = "managed=true"
  create = true

  depends_on = [ansibleops_directory.smoke]
}
