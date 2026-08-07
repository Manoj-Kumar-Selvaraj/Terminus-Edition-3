variable "engagement" {
  type = string
}

variable "waf" {
  type = object({
    id   = string
    mode = string
    rules = list(object({
      id     = string
      action = string
      match  = string
    }))
  })

  validation {
    condition     = length(var.waf.rules) >= 1
    error_message = "waf.rules must not be empty."
  }

  validation {
    condition = alltrue([
      for r in var.waf.rules : contains(["block", "allow"], r.action)
    ])
    error_message = "each waf rule action must be block or allow."
  }
}

variable "final_mode" {
  type        = string
  description = "Mode written to the live API. Contract requires enforce for DNS cutover."
  default     = "enforce"

  validation {
    condition     = contains(["enforce", "detect"], var.final_mode)
    error_message = "final_mode must be enforce or detect."
  }
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
