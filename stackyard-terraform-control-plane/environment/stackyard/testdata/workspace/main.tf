terraform {
  required_version = ">= 1.0"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

resource "null_resource" "example" {
  triggers = {
    tag = var.image_tag
  }
}
