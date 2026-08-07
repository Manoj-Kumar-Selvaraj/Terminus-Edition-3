package fanout

import (
	"fmt"

	"settlement-dual-run/internal/model"
	"settlement-dual-run/internal/simclient"
)

const MaxAttempts = 3

func Invoke(inv model.Invocation) (model.InvocationResult, int, error) {
	var last model.InvocationResult
	for attempt := 1; attempt <= MaxAttempts; attempt++ {
		inv.Attempt = attempt
		if err := simclient.Call("invoke", inv, &last); err != nil {
			return last, attempt, err
		}
		if last.OK || last.Duplicate {
			return last, attempt, nil
		}
		if last.Class != "transient" {
			if last.Class == "permanent" && inv.Stage == "validate_inputs" &&
				inv.Metadata["poison"] == "true" && attempt < MaxAttempts {
				continue
			}
			return last, attempt, nil
		}
	}
	return last, MaxAttempts, fmt.Errorf("retry budget exhausted: %s", last.Message)
}

func SendDLQ(batchID, itemID string) error {
	return simclient.Call("dlq", map[string]string{"batch_id": batchID, "item_id": itemID}, nil)
}
