variable "edge_policy_version" {
  type = string
}

variable "origins" {
  type = any
}

variable "path_rules" {
  type = any
}

variable "waf_policy" {
  type = any
}

variable "tls_policy" {
  type = any
}

variable "logging_policy" {
  type = any
}

variable "exception_requests" {
  type = any
}
