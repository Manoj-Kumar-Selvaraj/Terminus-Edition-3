variable "engagement" {
  type        = string
  description = "Engagement id stamped into provisioner markers."

  validation {
    condition     = length(var.engagement) >= 4
    error_message = "engagement must be at least 4 characters."
  }
}

variable "networks" {
  type = map(object({
    id          = string
    cidr        = string
    region      = string
    status      = string
    az          = optional(string)
    fabric_tier = optional(string)
  }))
  description = "Inventory networks keyed by network id."

  validation {
    condition     = length(var.networks) >= 1
    error_message = "at least one network is required."
  }

  validation {
    condition = alltrue([
      for k, n in var.networks : n.id == k
    ])
    error_message = "each networks map key must equal the nested id."
  }

  validation {
    condition = alltrue([
      for n in values(var.networks) : contains(["ready", "pending", "draining"], n.status)
    ])
    error_message = "network status must be ready, pending, or draining."
  }

  validation {
    condition = alltrue([
      for n in values(var.networks) : can(regex("^\\d+\\.\\d+\\.\\d+\\.\\d+/\\d+$", n.cidr))
    ])
    error_message = "each network cidr must look like an IPv4 CIDR."
  }
}

variable "edgectl_put_bin" {
  type        = string
  description = "Path to edgectl-put."
}

variable "payload_dir" {
  type        = string
  description = "Directory for rendered network JSON payloads."
}

variable "base_url" {
  type        = string
  description = "Live control plane base URL (informational for triggers)."
}
