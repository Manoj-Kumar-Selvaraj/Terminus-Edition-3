variable "environment" {
  type    = string
  default = "staging"
}

variable "inventory" {
  type = any
}

variable "endpoints" {
  type = any
}

variable "dns_zones" {
  type = any
}

variable "allowed_sources" {
  type = any
}
