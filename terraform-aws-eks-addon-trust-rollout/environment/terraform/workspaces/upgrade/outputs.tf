# Workspace outputs for upgrade workspace

output "addon_versions" {
  description = "EKS Add-on versions from upgrade module"
  value       = module.upgrade.addon_versions
}
