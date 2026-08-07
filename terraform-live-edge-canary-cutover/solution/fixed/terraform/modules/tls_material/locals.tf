locals {
  body = {
    id          = var.tls_id
    hostname    = var.hostname
    fingerprint = var.fingerprint
  }

  marker       = sha256(jsonencode(local.body))
  payload_path = "${var.payload_dir}/${var.tls_id}.json"

  certificate_profile = {
    key_algorithm     = "ECDSA-P256"
    signature         = "ecdsa-with-SHA256"
    san_dns           = [var.hostname]
    must_staple       = false
    min_days_remaining = 14
    rotation_runbook  = [
      "Issue replacement leaf with identical SANs.",
      "PUT /v1/tls/${var.tls_id} with the new fingerprint.",
      "Confirm traffic_guard still passes within error budget.",
    ]
  }

  fingerprint_parts = {
    prefix = substr(var.fingerprint, 0, 8)
    mid    = substr(var.fingerprint, 8, 48)
    suffix = substr(var.fingerprint, 56, 8)
  }

  trust_notes = [
    "Fingerprint must equal inventory tls_fingerprint exactly.",
    "Hostname must equal inventory edge_hostname exactly.",
    "DNS cutover is rejected unless this TLS object exists.",
    "Do not reuse fingerprints across engagements.",
    "Engagement ${var.engagement} owns this leaf for the weekend window.",
  ]
}
