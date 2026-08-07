terraform {
  required_version = ">= 1.5.0"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.3"
    }
  }
  backend "http" {
    address        = "http://127.0.0.1:18765/v1/workspaces/stage/state"
    lock_address   = "http://127.0.0.1:18765/v1/workspaces/stage/lock"
    unlock_address = "http://127.0.0.1:18765/v1/workspaces/stage/lock"
    lock_method    = "LOCK"
    unlock_method  = "UNLOCK"
  }
}

variable "marker" {
  type    = string
  default = "stage-default"
}

resource "null_resource" "marker" {
  triggers = {
    marker = var.marker
  }
}

output "marker" {
  value = var.marker
}
