locals {
  inventory_raw = jsondecode(file(var.inventory_file))

  engagement        = local.inventory_raw.engagement
  edge_hostname     = local.inventory_raw.edge_hostname
  error_budget_pct  = tonumber(local.inventory_raw.error_budget_pct)
  canary_steps      = [for s in local.inventory_raw.canary_steps : tonumber(s)]
  canary_route_id   = local.inventory_raw.canary_route_id
  networks          = local.inventory_raw.networks
  blue_pool         = local.inventory_raw.blue_pool
  green_pool        = local.inventory_raw.green_pool
  waf               = local.inventory_raw.waf
  tls_id            = local.inventory_raw.tls_id
  tls_fingerprint   = local.inventory_raw.tls_fingerprint
  dns_zone          = local.inventory_raw.dns_zone
  dns_name          = local.inventory_raw.dns_name
  observatory_probes = local.inventory_raw.observatory_probes

  phase_order = [
    "network_fabric",
    "origin_pool",
    "waf_policy",
    "tls_material",
    "canary_route",
    "dns_cutover",
    "observatory",
    "traffic_guard",
  ]

  green_pool_id = local.green_pool.id
  blue_pool_id  = local.blue_pool.id

  cutover_context = {
    engagement       = local.engagement
    hostname         = local.edge_hostname
    canary_route_id  = local.canary_route_id
    canary_steps     = local.canary_steps
    error_budget_pct = local.error_budget_pct
    dns_fqdn         = "${local.dns_name}.${local.dns_zone}"
    waf_id           = local.waf.id
    tls_id           = local.tls_id
    blue_pool_id     = local.blue_pool_id
    green_pool_id    = local.green_pool_id
  }
}

check "inventory_canary_steps_present" {
  assert {
    condition     = length(local.canary_steps) >= 1
    error_message = "inventory canary_steps must contain at least one weight."
  }
}

check "inventory_final_canary_is_100" {
  assert {
    condition     = local.canary_steps[length(local.canary_steps) - 1] == 100
    error_message = "inventory canary_steps must end at weight 100."
  }
}

check "inventory_error_budget_positive" {
  assert {
    condition     = local.error_budget_pct > 0 && local.error_budget_pct <= 100
    error_message = "inventory error_budget_pct must be in (0, 100]."
  }
}

module "network_fabric" {
  source = "./modules/network_fabric"

  engagement      = local.engagement
  networks        = local.networks
  edgectl_put_bin = var.edgectl_put_bin
  payload_dir     = "${var.payload_dir}/networks"
  base_url        = var.edgectl_base_url
}

module "origin_pool" {
  source = "./modules/origin_pool"

  engagement      = local.engagement
  blue_pool       = local.blue_pool
  green_pool      = local.green_pool
  network_ids     = module.network_fabric.ready_network_ids
  edgectl_put_bin = var.edgectl_put_bin
  payload_dir     = "${var.payload_dir}/pools"
  base_url        = var.edgectl_base_url

  depends_on = [module.network_fabric]
}

module "waf_policy" {
  source = "./modules/waf_policy"

  engagement      = local.engagement
  waf             = local.waf
  # BROKEN: detect mode is insufficient for DNS cutover
  final_mode      = "detect"
  edgectl_put_bin = var.edgectl_put_bin
  payload_dir     = "${var.payload_dir}/waf"
  base_url        = var.edgectl_base_url

  depends_on = [module.origin_pool]
}

module "tls_material" {
  source = "./modules/tls_material"

  engagement      = local.engagement
  tls_id          = local.tls_id
  hostname        = local.edge_hostname
  # BROKEN: fingerprint does not match inventory
  fingerprint     = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  edgectl_put_bin = var.edgectl_put_bin
  payload_dir     = "${var.payload_dir}/tls"
  base_url        = var.edgectl_base_url

  depends_on = [module.origin_pool]
}

module "canary_route" {
  source = "./modules/canary_route"

  engagement               = local.engagement
  route_id                 = local.canary_route_id
  blue_pool_id             = local.blue_pool_id
  green_pool_id            = local.green_pool_id
  # BROKEN: jump to weight 100 before walking 10/25/50/75
  canary_steps             = concat([100], [for s in local.canary_steps : s if s != 100])
  require_monotonic        = false
  error_budget_pct         = local.error_budget_pct
  edgectl_put_bin          = var.edgectl_put_bin
  payload_dir              = "${var.payload_dir}/canary"
  base_url                 = var.edgectl_base_url
  blue_pool_applied_id     = module.origin_pool.blue_pool_id
  green_pool_applied_id    = module.origin_pool.green_pool_id
  waf_applied_id           = module.waf_policy.waf_id
  tls_applied_id           = module.tls_material.tls_id

  depends_on = [
    module.origin_pool,
    module.waf_policy,
    module.tls_material,
  ]
}

module "dns_cutover" {
  source = "./modules/dns_cutover"

  engagement           = local.engagement
  zone                 = local.dns_zone
  name                 = local.dns_name
  target_pool          = local.green_pool_id
  require_canary_weight = 100
  require_waf_enforce  = true
  edgectl_put_bin      = var.edgectl_put_bin
  payload_dir          = "${var.payload_dir}/dns"
  base_url             = var.edgectl_base_url
  # BROKEN: not wired to canary_route final step
  final_canary_step_id = "unwired-skip-canary"
  waf_mode             = module.waf_policy.applied_mode
  tls_fingerprint      = module.tls_material.applied_fingerprint

  # BROKEN: missing module.canary_route — DNS can race ahead of weight 100
  depends_on = [
    module.waf_policy,
    module.tls_material,
  ]
}

module "observatory" {
  source = "./modules/observatory"

  engagement = local.engagement
  hostname   = local.edge_hostname
  probes     = local.observatory_probes
  output_dir = var.observatory_dir
  dns_fqdn   = "${local.dns_name}.${local.dns_zone}"
  green_pool = local.green_pool_id

  depends_on = [module.dns_cutover]
}

module "traffic_guard" {
  source = "./modules/traffic_guard"

  # BROKEN: guard skipped and budget inflated if re-enabled
  enabled            = false
  engagement         = local.engagement
  edgectl_put_bin    = var.edgectl_put_bin
  base_url           = var.edgectl_base_url
  max_error_rate_pct = 100.0
  expect_weight      = 100
  expect_pool        = local.green_pool_id
  dns_target_pool    = module.dns_cutover.target_pool
  observatory_ready  = module.observatory.probe_count

  depends_on = [
    module.dns_cutover,
    module.observatory,
  ]
}
