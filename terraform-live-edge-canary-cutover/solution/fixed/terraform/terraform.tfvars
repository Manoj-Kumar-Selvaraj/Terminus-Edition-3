inventory_file           = "inventory/edge-fleet.auto.tfvars.json"
edgectl_put_bin          = "/app/bin/edgectl-put"
edgectl_base_url         = "http://127.0.0.1:8787"
payload_dir              = "/app/var/edge/terraform-payloads"
observatory_dir          = "/app/var/edge/observatory"
traffic_guard_enabled    = true
require_canary_monotonic = true
waf_final_mode           = "enforce"
