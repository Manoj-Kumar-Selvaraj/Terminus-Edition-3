variable "inventory_file" {
  type        = string
  description = "Absolute or module-relative path to the edge fleet inventory JSON document."

  validation {
    condition     = length(trimspace(var.inventory_file)) > 0
    error_message = "inventory_file must be a non-empty path."
  }
}

variable "edgectl_put_bin" {
  type        = string
  description = "Path to the edgectl-put helper that Terraform local-exec provisioners invoke."
  default     = "/app/bin/edgectl-put"

  validation {
    condition     = startswith(var.edgectl_put_bin, "/")
    error_message = "edgectl_put_bin must be an absolute path."
  }
}

variable "edgectl_base_url" {
  type        = string
  description = "Base URL for the live edge control plane."
  default     = "http://127.0.0.1:8787"

  validation {
    condition     = startswith(var.edgectl_base_url, "http://127.0.0.1:")
    error_message = "edgectl_base_url must target the loopback control plane."
  }
}

variable "payload_dir" {
  type        = string
  description = "Directory where rendered JSON payloads for edgectl-put are written."
  default     = "/app/var/edge/terraform-payloads"
}

variable "observatory_dir" {
  type        = string
  description = "Directory where observatory probe specifications are materialized."
  default     = "/app/var/edge/observatory"
}

variable "traffic_guard_enabled" {
  type        = bool
  description = "When true, traffic_guard asserts live metrics after DNS cutover."
  default     = true
}

variable "require_canary_monotonic" {
  type        = bool
  description = "When true, canary_route validates that inventory canary_steps are strictly increasing."
  default     = true
}

variable "waf_final_mode" {
  type        = string
  description = "Final WAF mode required before DNS cutover. Contract requires enforce."
  default     = "enforce"

  validation {
    condition     = contains(["enforce", "detect"], var.waf_final_mode)
    error_message = "waf_final_mode must be enforce or detect."
  }
}
