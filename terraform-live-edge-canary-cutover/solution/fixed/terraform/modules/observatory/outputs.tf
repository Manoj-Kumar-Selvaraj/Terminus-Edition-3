output "probe_count" {
  value = length(var.probes)
}

output "probe_ids" {
  value = [for p in var.probes : p.id]
}

output "output_dir" {
  value = var.output_dir
}

output "index_path" {
  value = "${var.output_dir}/index.json"
}

output "ready_marker" {
  value = null_resource.observatory_ready_marker.id
}
