variable "engagement" {
  type = string
}

variable "tls_id" {
  type = string

  validation {
    condition     = length(var.tls_id) >= 3
    error_message = "tls_id must be non-trivial."
  }
}

variable "hostname" {
  type = string

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.hostname))
    error_message = "hostname must be a lowercase DNS name."
  }
}

variable "fingerprint" {
  type = string

  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.fingerprint))
    error_message = "fingerprint must be a 64-char lowercase hex sha256."
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
