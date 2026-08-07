variable "enabled" {
  type    = bool
  default = true
}

variable "engagement" {
  type = string
}

variable "edgectl_put_bin" {
  type = string
}

variable "base_url" {
  type = string
}

variable "max_error_rate_pct" {
  type = number

  validation {
    condition     = var.max_error_rate_pct > 0 && var.max_error_rate_pct <= 100
    error_message = "max_error_rate_pct must be in (0, 100]."
  }
}

variable "expect_weight" {
  type    = number
  default = 100

  validation {
    condition     = var.expect_weight == 100
    error_message = "traffic_guard expects canary weight 100 after cutover."
  }
}

variable "expect_pool" {
  type = string
}

variable "dns_target_pool" {
  type = string
}

variable "observatory_ready" {
  type = number
}
