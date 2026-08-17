package model

import "encoding/json"

const (
	TableTenant = "tenant"
	TableSKU    = "sku"
	TableOffer  = "offer"
	TableHold   = "hold"
)

var Tables = []string{TableTenant, TableSKU, TableOffer, TableHold}

var FKRank = map[string]int{
	TableTenant: 0,
	TableSKU:    1,
	TableOffer:  2,
	TableHold:   3,
}

type RowVersion struct {
	Table     string
	PK        string
	Xmin      int64
	Xmax      *int64
	Committed bool
	LSN       int64
	Payload   map[string]any
}

type WalRecord struct {
	LSN    int64          `json:"lsn"`
	TxnID  int64          `json:"txn_id"`
	Kind   string         `json:"kind"`
	Epoch  int64          `json:"epoch"`
	Table  string         `json:"table,omitempty"`
	PK     string         `json:"pk,omitempty"`
	Before map[string]any `json:"before"`
	After  map[string]any `json:"after"`
}

type Mutation struct {
	Op      string         `json:"op"`
	Table   string         `json:"table"`
	PK      string         `json:"pk"`
	Payload map[string]any `json:"payload"`
}

type Reject struct {
	TxnID  int64  `json:"txn_id"`
	Code   string `json:"code"`
	Table  string `json:"table"`
	PK     string `json:"pk"`
	Detail string `json:"detail"`
}

type ReplicaSlot struct {
	Epoch         int64 `json:"epoch"`
	ConfirmedLSN  int64 `json:"confirmed_lsn"`
}

type CDCEvent struct {
	LSN    int64          `json:"lsn"`
	TxnID  int64          `json:"txn_id"`
	Epoch  int64          `json:"epoch"`
	Table  string         `json:"table"`
	Op     string         `json:"op"`
	PK     string         `json:"pk"`
	Before map[string]any `json:"before"`
	After  map[string]any `json:"after"`
}

func UniqueKey(tenantID, code string) string {
	return tenantID + "\x00" + code
}

func MustJSON(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return "{}"
	}
	return string(b)
}

func CopyMap(src map[string]any) map[string]any {
	if src == nil {
		return nil
	}
	out := make(map[string]any, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func RowKey(table, pk string) string {
	return table + "/" + pk
}

func KindOp(kind string) string {
	switch kind {
	case "INSERT":
		return "insert"
	case "UPDATE":
		return "update"
	case "DELETE":
		return "delete"
	default:
		return ""
	}
}

func OpKind(op string) string {
	switch op {
	case "insert":
		return "INSERT"
	case "update":
		return "UPDATE"
	case "delete":
		return "DELETE"
	default:
		return ""
	}
}
