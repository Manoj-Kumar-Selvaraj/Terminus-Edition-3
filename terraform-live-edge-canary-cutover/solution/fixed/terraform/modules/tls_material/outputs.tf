output "tls_id" {
  value = var.tls_id
}

output "applied_fingerprint" {
  value = var.fingerprint
}

output "hostname" {
  value = var.hostname
}

output "payload_path" {
  value = local.payload_path
}

output "certificate_profile" {
  value = local.certificate_profile
}
