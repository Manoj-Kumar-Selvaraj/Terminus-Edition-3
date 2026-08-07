locals {
  cmdb     = jsondecode(file("/app/data/cmdb.json"))
  disks    = jsondecode(file("/app/data/disks.json"))
  defaults = jsondecode(file("/app/data/defaults.json"))
  windows  = jsondecode(file("/app/data/windows.json"))
}

module "wave" {
  source = "../../modules/wave"

  cmdb     = local.cmdb
  disks    = local.disks
  defaults = local.defaults
  windows  = local.windows
}
