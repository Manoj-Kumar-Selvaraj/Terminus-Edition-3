package schema

import "catalog/internal/model"

var required = map[string][]string{
	model.TableTenant: {"tenant_id", "status"},
	model.TableSKU:    {"sku_id", "tenant_id", "sku_code"},
	model.TableOffer:  {"offer_id", "tenant_id", "sku_id", "offer_code", "qty_on_hand"},
	model.TableHold:   {"hold_id", "tenant_id", "offer_id", "qty"},
}

func KnownTable(name string) bool {
	_, ok := model.FKRank[name]
	return ok
}

func FKRank(table string) int {
	if v, ok := model.FKRank[table]; ok {
		return v
	}
	return 99
}

func UniqueSpec(table string) (string, string, bool) {
	switch table {
	case model.TableSKU:
		return "tenant_id", "sku_code", true
	case model.TableOffer:
		return "tenant_id", "offer_code", true
	default:
		return "", "", false
	}
}

func MissingRequired(table string, payload map[string]any) string {
	for _, field := range required[table] {
		if _, ok := payload[field]; !ok {
			return field
		}
		if payload[field] == nil || payload[field] == "" {
			return field
		}
	}
	return ""
}

func PayloadPK(table, pk string, payload map[string]any) bool {
	switch table {
	case model.TableTenant:
		return str(payload["tenant_id"]) == pk
	case model.TableSKU:
		return str(payload["sku_id"]) == pk
	case model.TableOffer:
		return str(payload["offer_id"]) == pk
	case model.TableHold:
		return str(payload["hold_id"]) == pk
	}
	return false
}

func IntField(payload map[string]any, field string) (int64, bool) {
	raw, ok := payload[field]
	if !ok {
		return 0, false
	}
	switch v := raw.(type) {
	case float64:
		if v != float64(int64(v)) {
			return 0, false
		}
		return int64(v), true
	case int64:
		return v, true
	case int:
		return int64(v), true
	case jsonNumber:
		n, err := v.Int64()
		return n, err == nil
	default:
		return 0, false
	}
}

type jsonNumber interface{ Int64() (int64, error) }

func ParentRef(table string) (string, string, bool) {
	switch table {
	case model.TableSKU:
		return model.TableTenant, "tenant_id", true
	case model.TableOffer:
		return model.TableSKU, "sku_id", true
	case model.TableHold:
		return model.TableOffer, "offer_id", true
	}
	return "", "", false
}

func str(v any) string {
	if v == nil {
		return ""
	}
	s, _ := v.(string)
	return s
}

func Str(payload map[string]any, field string) string {
	return str(payload[field])
}

func PKField(table string) string {
	switch table {
	case model.TableTenant:
		return "tenant_id"
	case model.TableSKU:
		return "sku_id"
	case model.TableOffer:
		return "offer_id"
	case model.TableHold:
		return "hold_id"
	default:
		return ""
	}
}

func ValidStatus(status string) bool {
	return status == "ACTIVE" || status == "FROZEN"
}

func ValidOp(op string) bool {
	return op == "insert" || op == "update" || op == "delete"
}

func CoerceInt(v any) (int64, bool) {
	switch n := v.(type) {
	case float64:
		if n != float64(int64(n)) {
			return 0, false
		}
		return int64(n), true
	case int64:
		return n, true
	case int:
		return int64(n), true
	case jsonNumber:
		i, err := n.Int64()
		return i, err == nil
	case string:
		if n == "" {
			return 0, false
		}
		var out int64
		for _, c := range n {
			if c < '0' || c > '9' {
				return 0, false
			}
			out = out*10 + int64(c-'0')
		}
		return out, true
	default:
		return 0, false
	}
}

func ReplicaPK(table string, row map[string]any) string {
	return Str(row, PKField(table))
}

func IndexBucket(table string) string {
	switch table {
	case model.TableSKU:
		return "sku_code"
	case model.TableOffer:
		return "offer_code"
	default:
		return ""
	}
}

