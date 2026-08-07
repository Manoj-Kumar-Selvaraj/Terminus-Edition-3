locals {
  fleet_registry = jsondecode(file("/app/data/fleet_registry.json"))
  node_topology  = jsondecode(file("/app/data/node_topology.json"))
  defaults       = jsondecode(file("/app/data/defaults.json"))
  plugin_catalog = jsondecode(file("/app/data/plugin_catalog.json"))
}

module "cells" {
  source = "../../modules/cells"

  fleet_registry = local.fleet_registry
  node_topology  = local.node_topology
  defaults       = local.defaults
  plugin_catalog = local.plugin_catalog
}
