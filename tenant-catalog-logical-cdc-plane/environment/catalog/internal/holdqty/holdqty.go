package holdqty

import "catalog/internal/schema"

func OK(offer map[string]any, holds []map[string]any) bool {
	onHand, ok := schema.IntField(offer, "qty_on_hand")
	if !ok || onHand < 0 {
		return false
	}
	offerID := schema.Str(offer, "offer_id")
	var total int64
	for _, h := range holds {
		if schema.Str(h, "offer_id") != offerID {
			continue
		}
		qty, ok := schema.IntField(h, "qty")
		if !ok || qty <= 0 {
			return false
		}
		total += qty
	}
	return total <= onHand
}
