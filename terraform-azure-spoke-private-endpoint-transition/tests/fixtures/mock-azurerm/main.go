package main

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"strings"

	"github.com/hashicorp/terraform-plugin-sdk/v2/diag"
	"github.com/hashicorp/terraform-plugin-sdk/v2/helper/schema"
	"github.com/hashicorp/terraform-plugin-sdk/v2/plugin"
)

func main() {
	plugin.Serve(&plugin.ServeOpts{ProviderFunc: Provider})
}

func Provider() *schema.Provider {
	return &schema.Provider{
		Schema: map[string]*schema.Schema{
			"features": {
				Type:     schema.TypeList,
				Required: true,
				MaxItems: 1,
				Elem:     &schema.Resource{Schema: map[string]*schema.Schema{}},
			},
			"skip_provider_registration": {
				Type:     schema.TypeBool,
				Optional: true,
				Default:  false,
			},
			"subscription_id": {Type: schema.TypeString, Optional: true, Default: "00000000-0000-0000-0000-000000000000"},
			"tenant_id":       {Type: schema.TypeString, Optional: true, Default: "00000000-0000-0000-0000-000000000000"},
			"client_id":       {Type: schema.TypeString, Optional: true},
			"client_secret":   {Type: schema.TypeString, Optional: true, Sensitive: true},
			"environment":     {Type: schema.TypeString, Optional: true, Default: "public"},
		},
		ResourcesMap: map[string]*schema.Resource{
			"azurerm_virtual_network":                          resourceVNet(),
			"azurerm_subnet":                                   resourceSubnet(),
			"azurerm_route_table":                              resourceRouteTable(),
			"azurerm_route":                                    resourceRoute(),
			"azurerm_subnet_route_table_association":            resourceAssoc("route"),
			"azurerm_private_dns_zone":                         resourcePrivateDNSZone(),
			"azurerm_private_dns_zone_virtual_network_link":    resourceDNSLink(),
			"azurerm_private_endpoint":                         resourcePrivateEndpoint(),
			"azurerm_network_security_group":                   resourceNSG(),
			"azurerm_subnet_network_security_group_association": resourceAssoc("nsg"),
			"azurerm_network_security_rule":                    resourceNSGRule(),
			"azurerm_monitor_diagnostic_setting":               resourceDiag(),
			"azurerm_management_lock":                          resourceLock(),
		},
	}
}

func synthID(parts ...string) string {
	h := sha1.Sum([]byte(strings.Join(parts, "|")))
	return "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Mock/" + hex.EncodeToString(h[:12])
}

func tagsSchema() *schema.Schema {
	return &schema.Schema{Type: schema.TypeMap, Optional: true, Elem: &schema.Schema{Type: schema.TypeString}}
}

func stringAttr(required bool) *schema.Schema {
	s := &schema.Schema{Type: schema.TypeString}
	if required {
		s.Required = true
	} else {
		s.Optional = true
	}
	return s
}

func withCRUD(idFn func(*schema.ResourceData) string, sch map[string]*schema.Schema) *schema.Resource {
	return &schema.Resource{
		CreateContext: func(ctx context.Context, d *schema.ResourceData, m interface{}) diag.Diagnostics {
			d.SetId(idFn(d))
			return nil
		},
		ReadContext: func(ctx context.Context, d *schema.ResourceData, m interface{}) diag.Diagnostics {
			return nil
		},
		UpdateContext: func(ctx context.Context, d *schema.ResourceData, m interface{}) diag.Diagnostics {
			return nil
		},
		DeleteContext: func(ctx context.Context, d *schema.ResourceData, m interface{}) diag.Diagnostics {
			d.SetId("")
			return nil
		},
		Schema: sch,
	}
}

func resourceVNet() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("vnet", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                stringAttr(true),
		"resource_group_name": stringAttr(true),
		"location":            stringAttr(true),
		"address_space": {
			Type:     schema.TypeList,
			Required: true,
			Elem:     &schema.Schema{Type: schema.TypeString},
		},
		"tags": tagsSchema(),
		"ddos_protection_plan": {
			Type:     schema.TypeList,
			Optional: true,
			MaxItems: 1,
			Elem: &schema.Resource{Schema: map[string]*schema.Schema{
				"id":     stringAttr(true),
				"enable": {Type: schema.TypeBool, Required: true},
			}},
		},
	})
}

func resourceSubnet() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("subnet", rd.Get("resource_group_name").(string), rd.Get("virtual_network_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                 stringAttr(true),
		"resource_group_name":  stringAttr(true),
		"virtual_network_name": stringAttr(true),
		"address_prefixes": {
			Type:     schema.TypeList,
			Required: true,
			Elem:     &schema.Schema{Type: schema.TypeString},
		},
		"private_endpoint_network_policies": {
			Type:     schema.TypeString,
			Optional: true,
			Default:  "Enabled",
		},
		"private_endpoint_network_policies_enabled": {
			Type:     schema.TypeBool,
			Optional: true,
		},
	})
}

func resourceRouteTable() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("rt", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                          stringAttr(true),
		"location":                      stringAttr(true),
		"resource_group_name":           stringAttr(true),
		"disable_bgp_route_propagation": {Type: schema.TypeBool, Optional: true, Default: false},
		"tags":                          tagsSchema(),
	})
}

func resourceRoute() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("route", rd.Get("resource_group_name").(string), rd.Get("route_table_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                   stringAttr(true),
		"resource_group_name":    stringAttr(true),
		"route_table_name":       stringAttr(true),
		"address_prefix":         stringAttr(true),
		"next_hop_type":          stringAttr(true),
		"next_hop_in_ip_address": stringAttr(false),
	})
}

func resourceAssoc(kind string) *schema.Resource {
	sch := map[string]*schema.Schema{
		"subnet_id": {Type: schema.TypeString, Required: true},
	}
	if kind == "nsg" {
		sch["network_security_group_id"] = stringAttr(true)
	} else {
		sch["route_table_id"] = stringAttr(true)
	}
	return withCRUD(func(rd *schema.ResourceData) string {
		if kind == "nsg" {
			return synthID("nsgassoc", rd.Get("subnet_id").(string), rd.Get("network_security_group_id").(string))
		}
		return synthID("rtassoc", rd.Get("subnet_id").(string), rd.Get("route_table_id").(string))
	}, sch)
}

func resourcePrivateDNSZone() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("pdz", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                stringAttr(true),
		"resource_group_name": stringAttr(true),
		"tags":                tagsSchema(),
	})
}

func resourceDNSLink() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("pdzlink", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                  stringAttr(true),
		"resource_group_name":   stringAttr(true),
		"private_dns_zone_name": stringAttr(true),
		"virtual_network_id":    stringAttr(true),
		"registration_enabled":  {Type: schema.TypeBool, Optional: true, Default: false},
		"tags":                  tagsSchema(),
	})
}

func resourcePrivateEndpoint() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("pe", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                stringAttr(true),
		"location":            stringAttr(true),
		"resource_group_name": stringAttr(true),
		"subnet_id":           stringAttr(true),
		"tags":                tagsSchema(),
		"private_service_connection": {
			Type:     schema.TypeList,
			Required: true,
			MaxItems: 1,
			Elem: &schema.Resource{Schema: map[string]*schema.Schema{
				"name":                           stringAttr(true),
				"private_connection_resource_id": stringAttr(true),
				"subresource_names": {
					Type:     schema.TypeList,
					Required: true,
					Elem:     &schema.Schema{Type: schema.TypeString},
				},
				"is_manual_connection": {Type: schema.TypeBool, Required: true},
			}},
		},
		"private_dns_zone_group": {
			Type:     schema.TypeList,
			Optional: true,
			MaxItems: 1,
			Elem: &schema.Resource{Schema: map[string]*schema.Schema{
				"name": stringAttr(true),
				"private_dns_zone_ids": {
					Type:     schema.TypeList,
					Required: true,
					Elem:     &schema.Schema{Type: schema.TypeString},
				},
			}},
		},
	})
}

func resourceNSG() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("nsg", rd.Get("resource_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                stringAttr(true),
		"location":            stringAttr(true),
		"resource_group_name": stringAttr(true),
		"tags":                tagsSchema(),
	})
}

func resourceNSGRule() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("nsgrule", rd.Get("resource_group_name").(string), rd.Get("network_security_group_name").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":                         stringAttr(true),
		"resource_group_name":          stringAttr(true),
		"network_security_group_name":  stringAttr(true),
		"priority":                     {Type: schema.TypeInt, Required: true},
		"direction":                    stringAttr(true),
		"access":                       stringAttr(true),
		"protocol":                     stringAttr(true),
		"source_port_range":            stringAttr(false),
		"destination_port_range":       stringAttr(false),
		"destination_port_ranges":      {Type: schema.TypeList, Optional: true, Elem: &schema.Schema{Type: schema.TypeString}},
		"source_address_prefix":        stringAttr(false),
		"source_address_prefixes":      {Type: schema.TypeList, Optional: true, Elem: &schema.Schema{Type: schema.TypeString}},
		"destination_address_prefix":   stringAttr(false),
		"destination_address_prefixes": {Type: schema.TypeList, Optional: true, Elem: &schema.Schema{Type: schema.TypeString}},
	})
}

func resourceDiag() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("diag", rd.Get("name").(string), rd.Get("target_resource_id").(string))
	}, map[string]*schema.Schema{
		"name":                       stringAttr(true),
		"target_resource_id":         stringAttr(true),
		"log_analytics_workspace_id": stringAttr(true),
		"enabled_log": {
			Type:     schema.TypeSet,
			Optional: true,
			Elem: &schema.Resource{Schema: map[string]*schema.Schema{
				"category": stringAttr(true),
			}},
		},
		"metric": {
			Type:     schema.TypeSet,
			Optional: true,
			Elem: &schema.Resource{Schema: map[string]*schema.Schema{
				"category": stringAttr(true),
				"enabled":  {Type: schema.TypeBool, Optional: true, Default: true},
			}},
		},
	})
}

func resourceLock() *schema.Resource {
	return withCRUD(func(rd *schema.ResourceData) string {
		return synthID("lock", rd.Get("scope").(string), rd.Get("name").(string))
	}, map[string]*schema.Schema{
		"name":       stringAttr(true),
		"scope":      stringAttr(true),
		"lock_level": stringAttr(true),
		"notes":      stringAttr(false),
	})
}
