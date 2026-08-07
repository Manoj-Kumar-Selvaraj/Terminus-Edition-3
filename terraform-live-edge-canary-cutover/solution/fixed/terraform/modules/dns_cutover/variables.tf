variable "engagement" {
  type = string
}

variable "zone" {
  type = string
}

variable "name" {
  type = string
}

variable "target_pool" {
  type = string
}

variable "require_canary_weight" {
  type    = number
  default = 100

  validation {
    condition     = var.require_canary_weight == 100
    error_message = "contract requires require_canary_weight = 100."
  }
}

variable "require_waf_enforce" {
  type    = bool
  default = true

  validation {
    condition     = var.require_waf_enforce
    error_message = "contract requires require_waf_enforce = true."
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

variable "final_canary_step_id" {
  type        = string
  description = "Opaque id from canary_route proving the final step was wired."
}

variable "waf_mode" {
  type = string
}

variable "tls_fingerprint" {
  type = string
}
