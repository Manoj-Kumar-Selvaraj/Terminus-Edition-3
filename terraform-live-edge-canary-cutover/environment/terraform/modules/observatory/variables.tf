variable "engagement" {
  type = string
}

variable "hostname" {
  type = string
}

variable "probes" {
  type = list(object({
    id                 = string
    name               = string
    path               = string
    method             = string
    expect_status      = number
    timeout_ms         = number
    headers            = map(string)
    region_preference  = string
  }))

  validation {
    condition     = length(var.probes) >= 1
    error_message = "at least one observatory probe is required."
  }
}

variable "output_dir" {
  type = string
}

variable "dns_fqdn" {
  type = string
}

variable "green_pool" {
  type = string
}
