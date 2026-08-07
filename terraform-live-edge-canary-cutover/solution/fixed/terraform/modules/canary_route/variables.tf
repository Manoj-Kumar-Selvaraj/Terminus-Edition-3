variable "engagement" {
  type = string
}

variable "route_id" {
  type = string
}

variable "blue_pool_id" {
  type = string
}

variable "green_pool_id" {
  type = string
}

variable "canary_steps" {
  type        = list(number)
  description = "Ordered green weights. Must be applied sequentially with depends_on chaining."

  validation {
    condition     = length(var.canary_steps) >= 1
    error_message = "canary_steps must not be empty."
  }

  validation {
    condition = alltrue([
      for s in var.canary_steps : s >= 0 && s <= 100
    ])
    error_message = "each canary step must be between 0 and 100."
  }
}

variable "require_monotonic" {
  type    = bool
  default = true
}

variable "error_budget_pct" {
  type = number
}

variable "edgectl_put_bin" {
  type = string
}

variable "payload_dir" {
  type = string
}

variable "base_url" {
  type = string
}

variable "blue_pool_applied_id" {
  type        = string
  description = "Echo from origin_pool to create an apply-time edge."
}

variable "green_pool_applied_id" {
  type = string
}

variable "waf_applied_id" {
  type = string
}

variable "tls_applied_id" {
  type = string
}
