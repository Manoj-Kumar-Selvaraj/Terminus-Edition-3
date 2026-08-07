variable "engagement" {
  type = string
}

variable "blue_pool" {
  type = object({
    id          = string
    network_id  = string
    color       = string
    min_healthy = number
    origins = list(object({
      id           = string
      host         = string
      port         = number
      healthy      = bool
      weight       = optional(number)
      protocol     = optional(string)
      region_hint  = optional(string)
    }))
  })

  validation {
    condition     = var.blue_pool.color == "blue"
    error_message = "blue_pool.color must be blue."
  }

  validation {
    condition     = var.blue_pool.min_healthy >= 1
    error_message = "blue_pool.min_healthy must be >= 1."
  }

  validation {
    condition     = length(var.blue_pool.origins) >= var.blue_pool.min_healthy
    error_message = "blue_pool must declare at least min_healthy origins."
  }
}

variable "green_pool" {
  type = object({
    id          = string
    network_id  = string
    color       = string
    min_healthy = number
    origins = list(object({
      id           = string
      host         = string
      port         = number
      healthy      = bool
      weight       = optional(number)
      protocol     = optional(string)
      region_hint  = optional(string)
    }))
  })

  validation {
    condition     = var.green_pool.color == "green"
    error_message = "green_pool.color must be green."
  }

  validation {
    condition     = var.green_pool.min_healthy >= 1
    error_message = "green_pool.min_healthy must be >= 1."
  }

              validation {
                condition     = length(var.green_pool.origins) >= var.green_pool.min_healthy
                error_message = "green_pool must declare at least min_healthy origins."
              }
            }

variable "network_ids" {
  type        = list(string)
  description = "Ready network ids from network_fabric."
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
